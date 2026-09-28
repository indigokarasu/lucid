import json
import tempfile
import unittest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming import DreamDomain, DreamKernel, EvidenceRef, JsonNamespaceStore
from dreaming.autobio import propose_self_observation
from dreaming.chronicle import ChroniclePatternSource


class FakePatterns:
    def mine(self, **kwargs):
        return [{
            "category": "initiative",
            "summary": "User messages repeatedly reject unnecessary confirmation.",
            "confidence": 0.8,
            "event_ids": ["evt1", "evt2"],
        }]


class FakeCore:
    interaction_patterns = FakePatterns()


class DreamingKernelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = JsonNamespaceStore(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_hold_never_changes_active_state(self):
        kernel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)
        c = kernel.propose(
            kind="test", text="candidate", confidence=0.8,
            evidence=[EvidenceRef("chronicle_event", "e1")], source="test",
        )
        result = kernel.decide(c, decision="hold")
        self.assertFalse(result.promoted)
        self.assertEqual(kernel.active(), [])

    def test_evidenceless_candidate_cannot_promote(self):
        kernel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)
        c = kernel.propose(kind="test", text="candidate", confidence=0.8, evidence=[], source="test")
        result = kernel.decide(c, decision="promote")
        self.assertEqual(result.decision, "block")
        self.assertFalse(result.promoted)

    def test_relationship_and_self_state_are_separate(self):
        rel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)
        selfk = DreamKernel(DreamDomain.SELF, self.store)
        c = propose_self_observation(selfk, observation_id="obs1", text="I deferred judgment.")
        selfk.decide(c, decision="promote")
        self.assertEqual(len(selfk.active()), 1)
        self.assertEqual(rel.active(), [])
        with self.assertRaises(ValueError):
            rel.decide(c, decision="promote")

    def test_chronicle_patterns_seed_relationship_candidates_with_event_refs(self):
        kernel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)
        candidates = ChroniclePatternSource(FakeCore()).propose(kernel)
        self.assertEqual(len(candidates), 1)
        self.assertEqual([e.ref_id for e in candidates[0].evidence], ["evt1", "evt2"])

    def test_store_writes_separate_namespace_files(self):
        rel = DreamKernel(DreamDomain.RELATIONSHIP, self.store)
        selfk = DreamKernel(DreamDomain.SELF, self.store)
        rel.propose(kind="a", text="r", confidence=0.5, evidence=[EvidenceRef("x", "1")], source="t")
        selfk.propose(kind="b", text="s", confidence=0.5, evidence=[EvidenceRef("x", "2")], source="t")
        self.assertTrue((Path(self.tmp.name) / "relationship.json").exists())
        self.assertTrue((Path(self.tmp.name) / "self.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
