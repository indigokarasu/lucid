"""Chronicle evidence adapter for relationship Dreaming."""

from __future__ import annotations

from .kernel import DreamDomain, DreamKernel, EvidenceRef


class ChroniclePatternSource:
    def __init__(self, core):
        self.core = core

    @classmethod
    def from_active_core(cls):
        try:
            from engine.core import ChronicleCore
        except ImportError as exc:
            raise RuntimeError("Chronicle is not installed in this Hermes runtime") from exc
        core = ChronicleCore.active()
        if core is None:
            raise RuntimeError("Chronicle is installed but no active ChronicleCore exists")
        if not hasattr(core, "interaction_patterns"):
            raise RuntimeError("Chronicle is too old: interaction pattern miner is unavailable")
        return cls(core)

    def patterns(self, **kwargs):
        return self.core.interaction_patterns.mine(**kwargs)

    def propose(self, kernel: DreamKernel, **kwargs):
        if kernel.domain is not DreamDomain.RELATIONSHIP:
            raise ValueError("Chronicle user patterns may only seed relationship Dreaming")
        out = []
        for pattern in self.patterns(**kwargs):
            evidence = [
                EvidenceRef(kind="chronicle_event", ref_id=event_id)
                for event_id in pattern.get("event_ids", [])
            ]
            out.append(
                kernel.propose(
                    kind=f"interaction_pattern:{pattern['category']}",
                    text=pattern["summary"],
                    confidence=float(pattern.get("confidence", 0.5)),
                    evidence=evidence,
                    source="chronicle.interaction_patterns",
                )
            )
        return out
