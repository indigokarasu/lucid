"""Domain-separated candidate/promotion kernel for OCAS Dreaming.

This is intentionally small and deterministic. Model-backed reflection may
produce candidates, but only this layer changes promoted state. Relationship
learning and Indigo self-evolution use different namespaces and a candidate
from one domain cannot be promoted by the other.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class DreamDomain(str, Enum):
    RELATIONSHIP = "relationship"
    SELF = "self"


@dataclass(frozen=True)
class EvidenceRef:
    kind: str
    ref_id: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class Candidate:
    candidate_id: str
    domain: str
    kind: str
    text: str
    confidence: float
    evidence: list[EvidenceRef] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence"] = [e.to_dict() for e in self.evidence]
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        return cls(
            candidate_id=value["candidate_id"],
            domain=value["domain"],
            kind=value["kind"],
            text=value["text"],
            confidence=float(value.get("confidence", 0.5)),
            evidence=[EvidenceRef(**e) for e in value.get("evidence", [])],
            source=value.get("source", ""),
        )


@dataclass
class PromotionResult:
    candidate_id: str
    domain: str
    decision: str
    promoted: bool
    reasons: list[str] = field(default_factory=list)


class JsonNamespaceStore:
    """One state file per Dreaming domain.

    A caller may point multiple kernels at the same root safely because the
    filenames are domain-scoped.  The store never merges relationship state
    into self state or vice versa.
    """

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root)

    def _path(self, domain: DreamDomain) -> Path:
        return self.root / f"{domain.value}.json"

    def load(self, domain: DreamDomain) -> dict[str, Any]:
        path = self._path(domain)
        if not path.exists():
            return {"domain": domain.value, "candidates": {}, "active": {}}
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("domain") != domain.value:
            raise ValueError("dream state namespace mismatch")
        value.setdefault("candidates", {})
        value.setdefault("active", {})
        return value

    def save(self, domain: DreamDomain, state: dict[str, Any]) -> None:
        if state.get("domain") != domain.value:
            raise ValueError("refusing to write cross-domain dream state")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(domain)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)


class DreamKernel:
    def __init__(self, domain: DreamDomain | str, store: JsonNamespaceStore):
        self.domain = DreamDomain(domain)
        self.store = store

    def propose(
        self,
        *,
        kind: str,
        text: str,
        confidence: float,
        evidence: list[EvidenceRef],
        source: str,
    ) -> Candidate:
        if not text.strip():
            raise ValueError("candidate text is required")
        material = json.dumps(
            {
                "domain": self.domain.value,
                "kind": kind,
                "text": text.strip(),
                "evidence": sorted((e.kind, e.ref_id) for e in evidence),
            },
            sort_keys=True,
        )
        cid = "dream_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
        candidate = Candidate(
            candidate_id=cid,
            domain=self.domain.value,
            kind=kind,
            text=text.strip(),
            confidence=max(0.0, min(1.0, float(confidence))),
            evidence=list(evidence),
            source=source,
        )
        state = self.store.load(self.domain)
        state["candidates"][cid] = candidate.to_dict()
        self.store.save(self.domain, state)
        return candidate

    def decide(
        self,
        candidate: Candidate,
        *,
        decision: str,
        reasons: list[str] | None = None,
    ) -> PromotionResult:
        reasons = list(reasons or [])
        if candidate.domain != self.domain.value:
            raise ValueError(
                f"cross-domain promotion denied: candidate={candidate.domain} kernel={self.domain.value}"
            )
        if decision not in {"promote", "hold", "block"}:
            raise ValueError("decision must be promote, hold, or block")

        state = self.store.load(self.domain)
        if candidate.candidate_id not in state["candidates"]:
            state["candidates"][candidate.candidate_id] = candidate.to_dict()

        promoted = False
        if decision == "promote":
            if not candidate.evidence:
                decision = "block"
                reasons.append("candidate has no authoritative evidence references")
            else:
                state["active"][candidate.candidate_id] = candidate.to_dict()
                promoted = True

        state["candidates"][candidate.candidate_id]["last_decision"] = decision
        state["candidates"][candidate.candidate_id]["decision_reasons"] = reasons
        self.store.save(self.domain, state)
        return PromotionResult(
            candidate_id=candidate.candidate_id,
            domain=self.domain.value,
            decision=decision,
            promoted=promoted,
            reasons=reasons,
        )

    def active(self) -> list[Candidate]:
        state = self.store.load(self.domain)
        return [Candidate.from_dict(v) for _, v in sorted(state["active"].items())]
