import json
import unittest

from dreaming.chronicle import (
    ChronicleDreamWriter,
    ChroniclePatternSource,
    resolve_agent_principal,
    resolve_user_subject,
)
from dreaming.kernel import Candidate, DreamDomain, EvidenceRef


def event(event_id, seq, *, owner="default", author=None, session="s1"):
    attribution = {}
    if author is not None:
        attribution = {"author": {"id": author, "name": author, "is_bot": False}}
    return {
        "event_id": event_id,
        "seq": seq,
        "type": "observed",
        "actor": "user",
        "owner": owner,
        "session_id": session,
        "payload": json.dumps({"attribution": attribution}),
    }


class FakeStore:
    def __init__(self, events, principals=None):
        self.events = {row["event_id"]: row for row in events}
        self._principals = principals or [
            {"principal_id": "default", "type": "agent", "display": "default"}
        ]

    def get_event(self, event_id):
        return self.events.get(event_id)

    def get_observed_user_events_since(self, since_seq=0, *, limit=None, before_seq=None):
        rows = [
            row for row in self.events.values()
            if row.get("actor") == "user" and int(row.get("seq") or 0) > since_seq
        ]
        if before_seq is not None:
            rows = [row for row in rows if int(row.get("seq") or 0) < before_seq]
        rows.sort(key=lambda row: int(row.get("seq") or 0), reverse=True)
        return rows if limit is None else rows[:limit]

    def get_events_by_type(self, type_, since_seq=0):
        return [
            row for row in sorted(self.events.values(), key=lambda row: row["seq"])
            if row.get("type") == type_ and row["seq"] > since_seq
        ]

    def all_principals(self):
        return list(self._principals)

    def get_principal(self, principal_id):
        return next(
            (row for row in self._principals if row["principal_id"] == principal_id),
            None,
        )

    def max_seq(self):
        return max((row["seq"] for row in self.events.values()), default=0)


class FakePatterns:
    def __init__(self, pattern):
        self.pattern = pattern
        self.calls = []

    def mine(self, **kwargs):
        self.calls.append(dict(kwargs))
        return [dict(self.pattern)]


class FakeCapture:
    def __init__(self, store):
        self.store = store
        self.calls = []

    def append(self, type_, payload, *, parents=None, actor="", owner="", trust_level=0):
        self.calls.append(
            {
                "type": type_,
                "payload": payload,
                "parents": list(parents or []),
                "actor": actor,
                "owner": owner,
                "trust_level": trust_level,
            }
        )
        event_id = "write-1"
        self.store.events[event_id] = {
            "event_id": event_id,
            "seq": self.store.max_seq() + 1,
            "type": type_,
            "actor": actor,
            "owner": owner,
            "session_id": "",
            "payload": json.dumps(payload),
        }
        return event_id


class FakeCore:
    def __init__(self, events, pattern=None, principals=None):
        self.store = FakeStore(events, principals)
        if pattern is None:
            pattern = {
                "category": "initiative",
                "summary": "User repeatedly rejects unnecessary confirmation.",
                "event_ids": [row["event_id"] for row in events],
                "support": len(events),
                "distinct_sessions": len({row["session_id"] for row in events}),
                "confidence": 0.9,
                "last_seq": max((row["seq"] for row in events), default=0),
            }
        self.interaction_patterns = FakePatterns(pattern)
        self.capture = FakeCapture(self.store)
        self.active_principal = "default"


class ChronicleAdapterTests(unittest.TestCase):
    def test_agent_principal_is_memory_owner(self):
        core = FakeCore([event("e1", 1), event("e2", 2)])
        self.assertEqual(resolve_agent_principal(core), "default")

    def test_no_author_metadata_uses_primary_user(self):
        core = FakeCore([event("e1", 1), event("e2", 2)])
        self.assertEqual(resolve_user_subject(core, "default"), "primary_user")

    def test_one_explicit_human_author_is_auto_resolved(self):
        core = FakeCore([
            event("e1", 1, author="u-42"),
            event("e2", 2, author="u-42"),
        ])
        self.assertEqual(resolve_user_subject(core, "default"), "u-42")

    def test_multiple_human_authors_fail_closed(self):
        core = FakeCore([
            event("e1", 1, author="u-1"),
            event("e2", 2, author="u-2"),
        ])
        with self.assertRaises(ValueError):
            resolve_user_subject(core, "default")

    def test_pattern_recomputes_over_history_but_requires_new_evidence(self):
        core = FakeCore([
            event("e1", 10, session="a"),
            event("e2", 20, session="b"),
            event("e3", 30, session="c"),
        ])
        source = ChroniclePatternSource(
            core,
            owner_principal_id="default",
            user_subject_id="primary_user",
        )
        self.assertEqual(source.patterns(since_seq=30), [])
        patterns = source.patterns(since_seq=20)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["support"], 3)
        self.assertEqual(core.interaction_patterns.calls[-1]["since_seq"], 0)

    def test_cross_owner_evidence_is_removed_before_support_count(self):
        rows = [
            event("e1", 1, owner="default", session="a"),
            event("e2", 2, owner="other-agent", session="b"),
            event("e3", 3, owner="default", session="c"),
        ]
        core = FakeCore(rows)
        source = ChroniclePatternSource(
            core,
            owner_principal_id="default",
            user_subject_id="primary_user",
        )
        patterns = source.patterns(since_seq=0)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["event_ids"], ["e1", "e3"])
        self.assertEqual(patterns[0]["support"], 2)

    def test_explicit_subject_rejects_other_author(self):
        rows = [
            event("e1", 1, author="u-1", session="a"),
            event("e2", 2, author="u-2", session="b"),
            event("e3", 3, author="u-1", session="c"),
        ]
        core = FakeCore(rows)
        source = ChroniclePatternSource(
            core,
            owner_principal_id="default",
            user_subject_id="u-1",
            allow_unattributed=False,
        )
        patterns = source.patterns(since_seq=0)
        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["event_ids"], ["e1", "e3"])

    def test_durable_write_uses_agent_owner_and_user_domain(self):
        rows = [
            event("e1", 1, author="u-1", session="a"),
            event("e2", 2, author="u-1", session="b"),
        ]
        core = FakeCore(rows)
        writer = ChronicleDreamWriter(
            core,
            owner_principal_id="default",
            user_subject_id="u-1",
            allow_unattributed=False,
        )
        candidate = Candidate(
            candidate_id="dream_test",
            domain=DreamDomain.RELATIONSHIP.value,
            kind="interaction_pattern:initiative",
            text="User repeatedly rejects unnecessary confirmation.",
            confidence=0.82,
            evidence=[
                EvidenceRef("chronicle_event", "e1"),
                EvidenceRef("chronicle_event", "e2"),
            ],
            source="test",
        )
        result = writer.write_relationship(candidate)
        self.assertTrue(result["verified"])
        call = core.capture.calls[-1]
        self.assertEqual(call["owner"], "default")
        self.assertEqual(call["payload"]["domain"], "user")
        self.assertEqual(
            call["payload"]["key"]["subject"],
            "relationship:u-1",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
