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

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        profile_id: str | None = None,
        principal_id: str | None = None,
        subject_id: str | None = None,
    ):
        self.root = Path(root)
        self.profile_id = profile_id
        self.principal_id = principal_id
        self.subject_id = subject_id

    def _path(self, domain: DreamDomain) -> Path:
        return self.root / f"{domain.value}.json"

    def load(self, domain: DreamDomain) -> dict[str, Any]:
        path = self._path(domain)
        if not path.exists():
            return {
                "domain": domain.value,
                "profile_id": self.profile_id,
                "principal_id": self.principal_id,
                "subject_id": self.subject_id,
                "candidates": {},
                "active": {},
                "runs": [],
            }
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("domain") != domain.value:
            raise ValueError("dream state namespace mismatch")
        if self.profile_id is not None and value.get("profile_id") not in (None, self.profile_id):
            raise ValueError("dream state profile mismatch")
        if self.principal_id is not None and value.get("principal_id") not in (None, self.principal_id):
            raise ValueError("dream state principal mismatch")
        if self.subject_id is not None and value.get("subject_id") not in (None, self.subject_id):
            raise ValueError("dream state subject mismatch")
        value.setdefault("profile_id", self.profile_id)
        value.setdefault("principal_id", self.principal_id)
        value.setdefault("subject_id", self.subject_id)
        value.setdefault("candidates", {})
        value.setdefault("active", {})
        value.setdefault("runs", [])
        return value

    def save(self, domain: DreamDomain, state: dict[str, Any]) -> None:
        if state.get("domain") != domain.value:
            raise ValueError("refusing to write cross-domain dream state")
        if self.profile_id is not None and state.get("profile_id") not in (None, self.profile_id):
            raise ValueError("refusing to write cross-profile dream state")
        if self.principal_id is not None and state.get("principal_id") not in (None, self.principal_id):
            raise ValueError("refusing to write cross-principal dream state")
        if self.subject_id is not None and state.get("subject_id") not in (None, self.subject_id):
            raise ValueError("refusing to write cross-subject dream state")
        state["profile_id"] = self.profile_id
        state["principal_id"] = self.principal_id
        state["subject_id"] = self.subject_id
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(domain)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def record_run(self, domain: DreamDomain, record: dict[str, Any], *, keep: int = 200) -> None:
        state = self.load(domain)
        runs = list(state.get("runs") or [])
        runs.append(dict(record))
        state["runs"] = runs[-max(1, int(keep)):]
        self.save(domain, state)


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
        if decision not in {"promote", "hold", "block"}:
            raise ValueError("decision must be promote, hold, or block")

        state = self.store.load(self.domain)
        stored_raw = state["candidates"].get(candidate.candidate_id)
        if stored_raw is None:
            raise ValueError("candidate was not proposed in this domain")
        stored = Candidate.from_dict(stored_raw)
        if stored.domain != self.domain.value:
            raise ValueError(
                f"stored candidate namespace mismatch: candidate={stored.domain} kernel={self.domain.value}"
            )

        promoted = False
        if decision == "promote":
            if not stored.evidence:
                decision = "block"
                reasons.append("candidate has no authoritative evidence references")
            else:
                state["active"][stored.candidate_id] = stored.to_dict()
                promoted = True

        state["candidates"][stored.candidate_id]["last_decision"] = decision
        state["candidates"][stored.candidate_id]["decision_reasons"] = reasons
        self.store.save(self.domain, state)
        return PromotionResult(
            candidate_id=stored.candidate_id,
            domain=stored.domain,
            decision=decision,
            promoted=promoted,
            reasons=reasons,
        )

    def active(self) -> list[Candidate]:
        state = self.store.load(self.domain)
        return [Candidate.from_dict(v) for _, v in sorted(state["active"].items())]
