"""Chronicle adapters for Lucid User Dreaming.

Chronicle currently owns captured interaction memory under the active agent
principal. Human authorship is represented by speaker attribution, while
user-memory semantics are represented by domain="user". Lucid therefore keeps
the Chronicle owner principal separate from the human relationship subject.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .kernel import Candidate, DreamDomain, DreamKernel, EvidenceRef


def _payload(row: dict[str, Any] | None) -> dict[str, Any]:
    if not row:
        return {}
    raw = row.get("payload")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        return value if isinstance(value, dict) else {}
    return {}


def _event_subject(row: dict[str, Any] | None) -> str | None:
    """Return explicit host author identity when Chronicle captured one."""
    payload = _payload(row)
    attribution = payload.get("attribution")
    if not isinstance(attribution, dict):
        return None
    author = attribution.get("author")
    if not isinstance(author, dict):
        return None
    author_id = str(author.get("id") or "").strip()
    if author_id:
        return author_id
    name = str(author.get("name") or "").strip()
    return name or None


def load_chronicle_core(hermes_home: str | Path):
    """Load Chronicle through its normal core API in a standalone cron process."""
    home = Path(hermes_home).expanduser().resolve()
    candidates = [home / "plugins" / "chronicle"]
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


def resolve_agent_principal(core, explicit: str | None = None) -> str:
    """Resolve the Chronicle owner principal (an agent), failing on ambiguity."""
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
            "Lucid needs --principal when Chronicle has zero or multiple agent principals"
        )
    return str(agents[0]["principal_id"])


def _recent_owned_user_events(core, owner_principal_id: str, *, limit: int = 1000):
    """Newest human-side observed events owned by the selected Chronicle principal."""
    if hasattr(core.store, "get_observed_user_events_since"):
        rows = core.store.get_observed_user_events_since(0, limit=limit)
    else:
        rows = list(reversed(core.store.get_events_by_type("observed", 0)[-limit:]))
    return [
        row for row in rows
        if row.get("actor") == "user" and row.get("owner") == owner_principal_id
    ]


def resolve_user_subject(
    core,
    owner_principal_id: str,
    explicit: str | None = None,
) -> str:
    """Resolve the human relationship subject independently of Chronicle owner."""
    if explicit:
        value = str(explicit).strip()
        if not value:
            raise ValueError("user subject cannot be empty")
        return value

    known = {
        subject
        for event in _recent_owned_user_events(core, owner_principal_id)
        if (subject := _event_subject(event))
    }
    if len(known) > 1:
        raise ValueError(
            "multiple human authors are present; User Dreaming requires --user-subject"
        )
    if len(known) == 1:
        return next(iter(known))
    return "primary_user"


def _matches_subject(
    event: dict[str, Any],
    *,
    user_subject_id: str,
    allow_unattributed: bool,
) -> bool:
    subject = _event_subject(event)
    if subject is None:
        return allow_unattributed
    return subject == user_subject_id


class ChroniclePatternSource:
    """Principal- and subject-scoped view of Chronicle descriptive patterns."""

    def __init__(
        self,
        core,
        *,
        owner_principal_id: str,
        user_subject_id: str,
        allow_unattributed: bool = True,
    ):
        self.core = core
        self.owner_principal_id = owner_principal_id
        self.user_subject_id = user_subject_id
        self.allow_unattributed = bool(allow_unattributed)

    def watermark(self) -> int:
        """Latest Chronicle sequence seen by this run."""
        try:
            return int(self.core.store.max_seq() or 0)
        except Exception:
            return 0

    def _scoped_pattern(self, pattern: dict[str, Any]) -> dict[str, Any] | None:
        events: list[dict[str, Any]] = []
        for event_id in pattern.get("event_ids", []):
            event = self.core.store.get_event(str(event_id))
            if event is None:
                continue
            if event.get("actor") != "user":
                continue
            if event.get("owner") != self.owner_principal_id:
                continue
            if not _matches_subject(
                event,
                user_subject_id=self.user_subject_id,
                allow_unattributed=self.allow_unattributed,
            ):
                continue
            events.append(event)

        if len(events) < 2:
            return None

        sessions = {
            str(event.get("session_id") or "")
            for event in events
            if event.get("session_id")
        }
        support = len(events)
        scoped = dict(pattern)
        scoped["event_ids"] = [str(event["event_id"]) for event in events]
        scoped["support"] = support
        scoped["distinct_sessions"] = len(sessions)
        scoped["confidence"] = round(
            min(0.95, 0.50 + (0.08 * support) + (0.03 * len(sessions))),
            3,
        )
        scoped["last_seq"] = max(int(event.get("seq") or 0) for event in events)
        return scoped

    def patterns(self, **kwargs):
        if not hasattr(self.core, "interaction_patterns"):
            raise RuntimeError("Chronicle interaction pattern miner is unavailable")

        since_seq = int(kwargs.pop("since_seq", 0) or 0)
        raw_patterns = self.core.interaction_patterns.mine(since_seq=0, **kwargs)
        out: list[dict[str, Any]] = []
        for pattern in raw_patterns:
            scoped = self._scoped_pattern(pattern)
            if scoped is None:
                continue
            if int(scoped.get("last_seq") or 0) <= since_seq:
                continue
            out.append(scoped)
        return out

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
        return [
            kernel.propose(
                kind=f"interaction_pattern:{pattern['category']}",
                text=pattern["summary"],
                confidence=float(pattern.get("confidence", 0.5)),
                evidence=self.evidence_for(pattern),
                source="chronicle.interaction_patterns",
            )
            for pattern in self.patterns(**kwargs)
        ]


class ChronicleDreamWriter:
    """Commit accepted user-domain derivations through Chronicle."""

    def __init__(
        self,
        core,
        *,
        owner_principal_id: str,
        user_subject_id: str,
        allow_unattributed: bool = True,
    ):
        self.core = core
        self.owner_principal_id = owner_principal_id
        self.user_subject_id = user_subject_id
        self.allow_unattributed = bool(allow_unattributed)
        row = core.store.get_principal(owner_principal_id)
        if row is None or str(row.get("type") or "").lower() != "agent":
            raise ValueError("ChronicleDreamWriter requires an agent owner principal")

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
            if event.get("owner") != self.owner_principal_id:
                raise ValueError(f"evidence belongs to another Chronicle principal: {event_id}")
            if not _matches_subject(
                event,
                user_subject_id=self.user_subject_id,
                allow_unattributed=self.allow_unattributed,
            ):
                raise ValueError(f"evidence belongs to another human subject: {event_id}")

        payload = {
            "kind": "note",
            "key": {
                "note_type": "user_dreaming",
                "subject": f"relationship:{self.user_subject_id}",
            },
            "body": candidate.text,
            "confidence": candidate.confidence,
            "source_event": event_ids[0],
            "source_type": "user_dreaming",
            "domain": "user",
            "extras": {
                "dream_candidate_id": candidate.candidate_id,
                "user_subject_id": self.user_subject_id,
                "evidence_event_ids": event_ids,
            },
        }
        event_id = self.core.capture.append(
            "asserted",
            payload,
            parents=event_ids,
            actor="system",
            owner=self.owner_principal_id,
            trust_level=2,
        )

        stored = self.core.store.get_event(event_id)
        verified = False
        if stored is not None and stored.get("owner") == self.owner_principal_id:
            decoded = _payload(stored)
            extras = decoded.get("extras") if isinstance(decoded.get("extras"), dict) else {}
            verified = (
                decoded.get("source_type") == "user_dreaming"
                and decoded.get("body") == candidate.text
                and extras.get("user_subject_id") == self.user_subject_id
            )
        return {"event_id": event_id, "verified": verified}
