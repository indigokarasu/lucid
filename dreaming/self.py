"""Self Dreaming: stage grounded Autobio observations for identity review."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .autobio import propose_self_observation
from .kernel import DreamDomain, DreamKernel


@dataclass(frozen=True)
class SelfGatePolicy:
    min_chars: int = 40

    def evaluate(self, text: str) -> tuple[str, list[str]]:
        body = text.strip()
        if not body:
            return "block", ["empty observation"]
        if len(body) < self.min_chars:
            return "hold", [f"observation shorter than {self.min_chars} chars"]
        return "promote", [f"observation_chars={len(body)}"]


@dataclass
class SelfDreamRun:
    run_id: str
    principal_id: str
    started_at: str
    finished_at: str = ""
    source_path: str = ""
    promoted: int = 0
    held: int = 0
    blocked: int = 0
    candidate_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "principal_id": self.principal_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "source_path": self.source_path,
            "promoted": self.promoted,
            "held": self.held,
            "blocked": self.blocked,
            "candidate_ids": list(self.candidate_ids),
        }


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


class SelfDreamRunner:
    """Promote only grounded self observations into Lucid's self staging set.

    Promotion here means "eligible evidence for Autobio", never "edit SOUL".
    """

    def __init__(
        self,
        *,
        principal_id: str,
        kernel: DreamKernel,
        gate: SelfGatePolicy | None = None,
    ):
        if kernel.domain is not DreamDomain.SELF:
            raise ValueError("SelfDreamRunner requires self domain")
        self.principal_id = principal_id
        self.kernel = kernel
        self.gate = gate or SelfGatePolicy()

    def run_file(self, path: str | Path) -> SelfDreamRun:
        source = Path(path).expanduser().resolve()
        text = source.read_text(encoding="utf-8")
        result = SelfDreamRun(
            run_id=f"self-dream-{uuid.uuid4().hex[:12]}",
            principal_id=self.principal_id,
            started_at=_now(),
            source_path=str(source),
        )
        candidate = propose_self_observation(
            self.kernel,
            observation_id=str(source),
            text=text,
        )
        result.candidate_ids.append(candidate.candidate_id)
        decision, reasons = self.gate.evaluate(text)
        self.kernel.decide(candidate, decision=decision, reasons=reasons)
        if decision == "promote":
            result.promoted = 1
        elif decision == "hold":
            result.held = 1
        else:
            result.blocked = 1
        result.finished_at = _now()
        self.kernel.store.record_run(self.kernel.domain, result.to_dict())
        return result
