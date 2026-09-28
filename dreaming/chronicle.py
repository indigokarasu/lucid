"""Chronicle adapters for Lucid User Dreaming.

Reads use Chronicle's descriptive interaction-pattern surface. Durable writes go
through ChronicleCore.capture.append so the event log, reducer, ACLs, and
provenance remain authoritative. Lucid never mutates Chronicle SQLite directly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .kernel import Candidate, DreamDomain, DreamKernel, EvidenceRef


def load_chronicle_core(hermes_home: str | Path):
    """Load Chronicle through its normal core API in a standalone cron process."""
    home = Path(hermes_home).expanduser().resolve()
    candidates = [home / "plugins" / "chronicle"]
    # A profile-scoped HERMES_HOME commonly looks like
    # <root>/profiles/<profile>. Plugins may be shared at <root>/plugins.
    if home.parent.name == "profiles":
        candidates.append(home.parent.parent / "plugins" / "chronicle")
    for path in candidates:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))
    try:
        from engine.core import ChronicleCore
    except ImportError as exc:
        raise RuntimeError(
            "Chronicle plugin is not importable from the profile or shared HERMES_HOME plugin roots"
        ) from exc
    return ChronicleCore.get(str(home))


def resolve_user_principal(core, explicit: str | None = None) -> str:
    """Resolve exactly one user principal or require an explicit id."""
    if explicit:
        row = core.store.get_principal(explicit)
        if row is None:
            raise ValueError(f"unknown Chronicle principal: {explicit}")
        if str(row.get("type") or "").lower() != "user":
            raise ValueError(f"principal {explicit} is not a user principal")
        return explicit
    users = [
        p for p in core.store.all_principals()
        if str(p.get("type") or "").lower() == "user"
    ]
    if len(users) != 1:
        raise ValueError(
            "User Dreaming needs --principal when Chronicle has zero or multiple user principals"
        )
    return str(users[0]["principal_id"])


def resolve_agent_principal(core, explicit: str | None = None) -> str:
    """Resolve an explicit agent principal, or the active agent if unambiguous."""
    if explicit:
        row = core.store.get_principal(explicit)
        if row is None:
            raise ValueError(f"unknown Chronicle principal: {explicit}")
        if str(row.get("type") or "").lower() != "agent":
            raise ValueError(f"principal {explicit} is not an agent principal")
        return explicit
    active = str(getattr(core, "active_principal", "") or "")
    row = core.store.get_principal(active) if active else None
    if row and str(row.get("type") or "").lower() == "agent":
        return active
    agents = [
        p for p in core.store.all_principals()
        if str(p.get("type") or "").lower() == "agent"
    ]
    if len(agents) != 1:
        raise ValueError(
            "Self Dreaming needs --principal when Chronicle has zero or multiple agent principals"
        )
    return str(agents[0]["principal_id"])


class ChroniclePatternSource:
    def __init__(self, core, *, principal_id: str | None = None):
        self.core = core
        self.principal_id = principal_id

    @classmethod
    def from_active_core(cls, *, principal_id: str | None = None):
        try:
            from engine.core import ChronicleCore
        except ImportError as exc:
            raise RuntimeError("Chronicle is not installed in this Hermes runtime") from exc
        core = ChronicleCore.active()
        if core is None:
            raise RuntimeError("Chronicle is installed but no active ChronicleCore exists")
        if not hasattr(core, "interaction_patterns"):
            raise RuntimeError("Chronicle is too old: interaction pattern miner is unavailable")
        return cls(core, principal_id=principal_id)

    def patterns(self, **kwargs):
        if not hasattr(self.core, "interaction_patterns"):
            raise RuntimeError("Chronicle interaction pattern miner is unavailable")
        patterns = self.core.interaction_patterns.mine(**kwargs)
        if not self.principal_id:
            return patterns
        scoped = []
        for pattern in patterns:
            ids = [str(x) for x in pattern.get("event_ids", []) if x]
            if not ids:
                continue
            events = [self.core.store.get_event(event_id) for event_id in ids]
            if any(event is None for event in events):
                continue
            if any(event.get("owner") != self.principal_id for event in events):
                continue
            scoped.append(pattern)
        return scoped

    @staticmethod
    def evidence_for(pattern: dict[str, Any]) -> list[EvidenceRef]:
        return [
            EvidenceRef(kind="chronicle_event", ref_id=str(event_id))
            for event_id in pattern.get("event_ids", [])
            if event_id
        ]

    def propose(self, kernel: DreamKernel, **kwargs):
        if kernel.domain is not DreamDomain.RELATIONSHIP:
            raise ValueError("Chronicle user patterns may only seed relationship Dreaming")
        out = []
        for pattern in self.patterns(**kwargs):
            out.append(
                kernel.propose(
                    kind=f"interaction_pattern:{pattern['category']}",
                    text=pattern["summary"],
                    confidence=float(pattern.get("confidence", 0.5)),
                    evidence=self.evidence_for(pattern),
                    source="chronicle.interaction_patterns",
                )
            )
        return out


class ChronicleDreamWriter:
    """Commit accepted user-owned relationship derivations through Chronicle."""

    def __init__(self, core, *, principal_id: str):
        self.core = core
        self.principal_id = principal_id
        row = core.store.get_principal(principal_id)
        if row is None or str(row.get("type") or "").lower() != "user":
            raise ValueError("ChronicleDreamWriter requires a user principal")

    def write_relationship(self, candidate: Candidate) -> dict[str, Any]:
        if candidate.domain != DreamDomain.RELATIONSHIP.value:
            raise ValueError("only relationship candidates may be written as user memory")
        event_ids = [
            ref.ref_id for ref in candidate.evidence
            if ref.kind == "chronicle_event" and ref.ref_id
        ]
        if not event_ids:
            raise ValueError("relationship candidate has no Chronicle event evidence")

        for event_id in event_ids:
            event = self.core.store.get_event(event_id)
            if event is None:
                raise ValueError(f"missing Chronicle evidence event: {event_id}")
            if event.get("actor") != "user":
                raise ValueError(f"evidence is not human-user attributed: {event_id}")
            if event.get("owner") != self.principal_id:
                raise ValueError(f"evidence belongs to another principal: {event_id}")

        payload = {
            "kind": "note",
            "key": {
                "note_type": "user_dreaming",
                "subject": "relationship",
            },
            "body": candidate.text,
            "confidence": candidate.confidence,
            "source_event": event_ids[0],
            "source_type": "user_dreaming",
            "domain": "user",
            "extras": {
                "dream_candidate_id": candidate.candidate_id,
                "evidence_event_ids": event_ids,
            },
        }
        event_id = self.core.capture.append(
            "asserted",
            payload,
            parents=event_ids,
            actor="system",
            owner=self.principal_id,
            trust_level=2,
        )
        stored = self.core.store.get_event(event_id)
        verified = False
        if stored is not None and stored.get("owner") == self.principal_id:
            raw = stored.get("payload")
            try:
                decoded = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except (TypeError, ValueError):
                decoded = {}
            verified = (
                decoded.get("source_type") == "user_dreaming"
                and decoded.get("body") == candidate.text
            )
        return {"event_id": event_id, "verified": verified}
