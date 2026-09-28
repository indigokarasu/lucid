import tempfile
import unittest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.kernel import DreamDomain, DreamKernel, EvidenceRef, JsonNamespaceStore
from dreaming.runtime import DreamScope
from dreaming.self import SelfDreamRunner
from dreaming.user import UserDreamRunner


class FakeSource:
    def __init__(self, patterns, watermark=0):
        self._patterns = patterns
        self._watermark = watermark

    def patterns(self, **kwargs):
        return list(self._patterns)

    def watermark(self):
        return self._watermark

    @staticmethod
    def evidence_for(pattern):
        return [
            EvidenceRef("chronicle_event", event_id)
            for event_id in pattern.get("event_ids", [])
        ]


class GoodWriter:
    def __init__(self):
        self.calls = []

    def write_relationship(self, candidate):
        self.calls.append(candidate.candidate_id)
        return {"event_id": "chronicle-write-1", "verified": True}


class BadWriter:
    def write_relationship(self, candidate):
        return {"event_id": "chronicle-write-1", "verified": False}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JsonNamespaceStore(
            self.tmp.name,
            profile_id="indigo",
            principal_id="agent-1",
            subject_id="user-1",
        )
        self.kernel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def pattern(self):
        return {
            "category": "initiative",
            "summary": "User repeatedly rejects unnecessary confirmation.",
            "confidence": 0.82,
            "support": 3,
            "distinct_sessions": 2,
            "event_ids": ["e1", "e2", "e3"],
            "last_seq": 44,
        }

    def test_user_dream_promotes_only_after_verified_write(self):
        writer = GoodWriter()
        run = UserDreamRunner(
            owner_principal_id="agent-1",
            user_subject_id="user-1",
            kernel=self.kernel,
            source=FakeSource([self.pattern()], watermark=44),
            writer=writer,
        ).run()
        self.assertEqual(run.promoted, 1)
        self.assertEqual(run.durable_writes, ["chronicle-write-1"])
        self.assertEqual(len(self.kernel.active()), 1)
        self.assertEqual(len(writer.calls), 1)
        self.assertEqual(run.last_seq, 44)
        self.assertEqual(run.owner_principal_id, "agent-1")
        self.assertEqual(run.user_subject_id, "user-1")

    def test_unverified_write_holds_candidate(self):
        run = UserDreamRunner(
            owner_principal_id="agent-1",
            user_subject_id="user-1",
            kernel=self.kernel,
            source=FakeSource([self.pattern()]),
            writer=BadWriter(),
        ).run()
        self.assertEqual(run.promoted, 0)
        self.assertEqual(run.held, 1)
        self.assertEqual(self.kernel.active(), [])

    def test_low_confidence_holds_without_writer_call(self):
        pattern = self.pattern()
        pattern["confidence"] = 0.4
        writer = GoodWriter()
        run = UserDreamRunner(
            owner_principal_id="agent-1",
            user_subject_id="user-1",
            kernel=self.kernel,
            source=FakeSource([pattern]),
            writer=writer,
        ).run()
        self.assertEqual(run.held, 1)
        self.assertEqual(writer.calls, [])
        self.assertEqual(self.kernel.active(), [])

    def test_store_rejects_other_principal_state(self):
        self.kernel.propose(
            kind="x",
            text="candidate",
            confidence=0.8,
            evidence=[EvidenceRef("chronicle_event", "e1")],
            source="test",
        )
        other = JsonNamespaceStore(
            self.tmp.name,
            profile_id="indigo",
            principal_id="agent-2",
            subject_id="user-1",
        )
        with self.assertRaises(ValueError):
            other.load(DreamDomain.RELATIONSHIP)

    def test_runtime_scope_places_state_under_owner_and_subject(self):
        scope = DreamScope.from_values(
            hermes_home=self.tmp.name,
            profile_id="indigo",
            principal_id="agent-1",
            subject_id="user-1",
        )
        self.assertTrue(
            str(scope.state_root).endswith(
                "commons/data/dreaming/profiles/indigo/principals/agent-1/subjects/user-1"
            )
        )

    def test_store_rejects_other_subject_state(self):
        self.kernel.propose(
            kind="x",
            text="candidate",
            confidence=0.8,
            evidence=[EvidenceRef("chronicle_event", "e1")],
            source="test",
        )
        other = JsonNamespaceStore(
            self.tmp.name,
            profile_id="indigo",
            principal_id="agent-1",
            subject_id="user-2",
        )
        with self.assertRaises(ValueError):
            other.load(DreamDomain.RELATIONSHIP)

    def test_no_pattern_still_advances_watermark(self):
        run = UserDreamRunner(
            owner_principal_id="agent-1",
            user_subject_id="user-1",
            kernel=self.kernel,
            source=FakeSource([], watermark=91),
            writer=GoodWriter(),
        ).run(since_seq=44)
        self.assertEqual(run.last_seq, 91)
        self.assertEqual(run.proposed, 0)

    def test_self_dream_promotes_only_self_state(self):
        root = Path(self.tmp.name) / "self-store"
        store = JsonNamespaceStore(
            root,
            profile_id="indigo",
            principal_id="agent-1",
            subject_id="agent-1",
        )
        kernel = DreamKernel(DreamDomain.SELF, store)
        obs = Path(self.tmp.name) / "2026-09-27.md"
        obs.write_text(
            "I deferred judgment twice today, then corrected course after explicit evidence.",
            encoding="utf-8",
        )
        run = SelfDreamRunner(
            principal_id="agent-1",
            kernel=kernel,
        ).run_file(obs)
        self.assertEqual(run.promoted, 1)
        self.assertEqual(len(kernel.active()), 1)
        self.assertEqual(kernel.active()[0].domain, "self")


if __name__ == "__main__":
    unittest.main(verbosity=2)
