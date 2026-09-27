#!/usr/bin/env python3
"""Smoke tests for the Lucid dream cycle template.

These are deliberately dependency-free and side-effect-free: they import the
template as a module and exercise the pure helpers plus the CLI contract, but
never run a real dream cycle and never touch the journal/log/config state
files. That last property is the point of the test -- an earlier version of
the template had no argument parsing, so `--help` executed a full 200-journal
cycle and mutated real state. These tests lock that shut.

Run:  python3 tests/test_smoke.py
Exit: 0 all passed, 1 one or more failures.
"""
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "lucid_dream_template.py"
SH_SCRIPT = REPO / "scripts" / "update.sh"


def load_template():
    spec = importlib.util.spec_from_file_location("lucid_dream_template", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestScriptContract(unittest.TestCase):
    """The CLI must be inspectable without executing a cycle."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True, text=True, timeout=60,
        )

    def test_help_exits_zero(self):
        r = self._run("--help")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_help_documents_every_flag(self):
        out = self._run("--help").stdout
        for flag in ("--dry-run", "--batch-size", "--json"):
            self.assertIn(flag, out, f"{flag} missing from --help")

    def test_help_states_exit_codes(self):
        self.assertIn("Exit codes", self._run("--help").stdout)

    def test_unknown_flag_exits_two(self):
        r = self._run("--definitely-not-a-flag")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_zero_batch_size_is_rejected(self):
        r = self._run("--batch-size", "0")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)


class TestUpdateScriptContract(unittest.TestCase):
    def test_help_exits_zero(self):
        r = subprocess.run(["bash", str(SH_SCRIPT), "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_help_exits_before_running_git(self):
        r = subprocess.run(["bash", str(SH_SCRIPT), "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertNotIn("HEAD is now at", r.stdout)

    def test_unknown_flag_exits_two(self):
        r = subprocess.run(["bash", str(SH_SCRIPT), "--nope"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_dry_run_does_not_reset(self):
        r = subprocess.run(["bash", str(SH_SCRIPT), "--dry-run", "--force"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[dry-run]", r.stdout)
        self.assertNotIn("HEAD is now at", r.stdout)


class TestPureHelpers(unittest.TestCase):
    """Classification and scan-detection helpers, no filesystem writes."""

    @classmethod
    def setUpClass(cls):
        cls.m = load_template()

    def test_scan_patterns_classify_known_scans(self):
        for name in ("forge-journal-scan-2026.json", "finch-daily-2026.json",
                     "spot-sweep-2026.json"):
            self.assertTrue(self.m.is_scan(name), f"{name} should be a scan")

    def test_skill_level_exceptions_are_not_scans(self):
        # These are the documented never-scan exceptions.
        for name in ("mentor-light-20260809T113119Z.json",
                     "dispatch-triage-2026.json",
                     "praxis-review-2026.json"):
            self.assertFalse(self.m.is_scan(name), f"{name} must not be a scan")

    def test_batch_size_default_is_two_hundred(self):
        self.assertEqual(self.m.DEFAULT_BATCH_SIZE, 200)

    def test_narrative_extraction_reads_nested_paths(self):
        journal = {
            "decision": {"reasoning_summary": "chose the cheaper path"},
            "run_identity": {"journal_type": "Action"},
        }
        text = self.m.extract_narrative(journal, "x.json")
        self.assertIn("chose the cheaper path", text)

    def test_entities_observed_int_is_tolerated(self):
        # Known type-guard case: entities_observed is sometimes an int.
        journal = {"decision": {"payload": {"entities_observed": 3}}}
        self.assertIsInstance(self.m.extract_narrative(journal, "x.json"), str)


class TestStateFilesAreNotMutatedByImport(unittest.TestCase):
    def test_import_has_no_side_effects(self):
        before = {p: p.stat().st_mtime for p in
                  (REPO / "scripts").iterdir() if p.is_file()}
        load_template()
        after = {p: p.stat().st_mtime for p in
                 (REPO / "scripts").iterdir() if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main(verbosity=2)
