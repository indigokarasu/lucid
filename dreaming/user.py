"""User Dreaming: Chronicle-grounded offline relationship consolidation."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from .kernel import Candidate, DreamDomain, DreamKernel


class PatternSource(Protocol):
    def patterns(self, **kwargs) -> list[dict[str, Any]]: ...
    def evidence_for(self, pattern: dict[str, Any]): ...
    def watermark(self) -> int: ...


class DurableUserWriter(Protocol):
    def write_relationship(self, candidate: Candidate) -> dict[str, Any]: ...


@dataclass(frozen=True)
class UserGatePolicy:
    min_confidence: float = 0.72
    min_support: int = 2

    def evaluate(self, candidate: Candidate, pattern: dict[str, Any]) -> tuple[str, list[str]]:
        reasons: list[str] = []
        support = int(pattern.get("support") or 0)
        if not candidate.evidence:
            return "block", ["no authoritative evidence references"]
        if support < self.min_support:
            return "hold", [f"support {support} < {self.min_support}"]
        if candidate.confidence < self.min_confidence:
            return "hold", [
                f"confidence {candidate.confidence:.3f} < {self.min_confidence:.3f}"
            ]
        reasons.append(f"support={support}")
        reasons.append(f"confidence={candidate.confidence:.3f}")
        return "promote", reasons


@dataclass
class UserDreamRun:
    run_id: str
    owner_principal_id: str
    user_subject_id: str
    started_at: str
    finished_at: str = ""
    seen_patterns: int = 0
    proposed: int = 0
    promoted: int = 0
    held: int = 0
    blocked: int = 0
    durable_writes: list[str] = field(default_factory=list)
    last_seq: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "owner_principal_id": self.owner_principal_id,
            "user_subject_id": self.user_subject_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "seen_patterns": self.seen_patterns,
            "proposed": self.proposed,
            "promoted": self.promoted,
            "held": self.held,
            "blocked": self.blocked,
            "durable_writes": list(self.durable_writes),
            "last_seq": self.last_seq,
            "errors": list(self.errors),
        }


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class UserDreamRunner:
    """Consolidate descriptive Chronicle patterns into verified user-owned memory.

    The runner never treats Lucid's own prior output as fresh evidence.
    A candidate is only promoted in Lucid after its Chronicle durable write
    succeeds and verifies.
    """

    def __init__(
        self,
        *,
        owner_principal_id: str,
        user_subject_id: str,
        kernel: DreamKernel,
        source: PatternSource,
        writer: DurableUserWriter,
        gate: UserGatePolicy | None = None,
    ):
        if kernel.domain is not DreamDomain.RELATIONSHIP:
            raise ValueError("UserDreamRunner requires relationship domain")
        self.owner_principal_id = owner_principal_id
        self.user_subject_id = user_subject_id
        self.kernel = kernel
        self.source = source
        self.writer = writer
        self.gate = gate or UserGatePolicy()

    def run(self, *, since_seq: int = 0, limit: int = 5000) -> UserDreamRun:
        result = UserDreamRun(
            run_id=f"user-dream-{uuid.uuid4().hex[:12]}",
            owner_principal_id=self.owner_principal_id,
            user_subject_id=self.user_subject_id,
            started_at=_now(),
        )
        patterns = self.source.patterns(since_seq=since_seq, limit=limit)
        result.seen_patterns = len(patterns)
        result.last_seq = max(since_seq, int(self.source.watermark() or 0))

        for pattern in patterns:
            evidence = self.source.evidence_for(pattern)
            candidate = self.kernel.propose(
                kind=f"interaction_pattern:{pattern.get('category', 'unknown')}",
                text=str(pattern.get("summary") or "").strip(),
                confidence=float(pattern.get("confidence") or 0.0),
                evidence=evidence,
                source="chronicle.interaction_patterns",
            )
            result.proposed += 1
            decision, reasons = self.gate.evaluate(candidate, pattern)
            if decision == "block":
                self.kernel.decide(candidate, decision="block", reasons=reasons)
                result.blocked += 1
                continue
            if decision == "hold":
                self.kernel.decide(candidate, decision="hold", reasons=reasons)
                result.held += 1
                continue

            try:
                write = self.writer.write_relationship(candidate)
            except Exception as exc:
                self.kernel.decide(
                    candidate,
                    decision="hold",
                    reasons=reasons + [f"durable write failed: {exc}"],
                )
                result.held += 1
                result.errors.append(f"{candidate.candidate_id}: {exc}")
                continue

            event_id = str(write.get("event_id") or "")
            if not event_id or not write.get("verified"):
                self.kernel.decide(
                    candidate,
                    decision="hold",
                    reasons=reasons + ["durable write did not verify"],
                )
                result.held += 1
                continue

            self.kernel.decide(
                candidate,
                decision="promote",
                reasons=reasons + [f"chronicle_event={event_id}"],
            )
            result.promoted += 1
            result.durable_writes.append(event_id)

        result.finished_at = _now()
        self.kernel.store.record_run(self.kernel.domain, result.to_dict())
        return result
