import unittest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.cron import LEGACY_CURATE, SELF_DREAM, USER_DREAM, reconcile


def job_from_spec(spec, job_id):
    return {
        "id": job_id,
        "name": spec.name,
        "schedule_display": spec.schedule,
        "prompt": spec.prompt,
        "deliver": spec.deliver,
        "enabled": True,
        "state": "scheduled",
        "skills": [spec.skill],
    }


class FakeBackend:
    def __init__(self, jobs=None):
        self.jobs = list(jobs or [])
        self.counter = 100

    def list_jobs(self):
        return [dict(j) for j in self.jobs]

    def create(self, spec):
        self.counter += 1
        self.jobs.append(job_from_spec(spec, f"j{self.counter}"))

    def edit(self, job_id, spec):
        for idx, job in enumerate(self.jobs):
            if str(job.get("id")) == str(job_id):
                self.jobs[idx] = job_from_spec(spec, str(job_id))
                return
        raise AssertionError(f"missing job {job_id}")

    def remove(self, job_id):
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if str(j.get("id")) != str(job_id)]
        if len(self.jobs) == before:
            raise AssertionError(f"missing job {job_id}")


class CronReconcileTests(unittest.TestCase):
    def test_migrates_legacy_job_and_creates_required_jobs(self):
        backend = FakeBackend(
            [{
                "id": "legacy",
                "name": "lucid:dream",
                "schedule_display": "12 10 * * *",
                "prompt": "old curator",
                "deliver": "local",
                "enabled": True,
                "state": "scheduled",
                "skills": [],
            }]
        )
        result = reconcile(backend)
        self.assertTrue(result["ok"])
        names = sorted(j["name"] for j in backend.jobs)
        self.assertEqual(
            names,
            sorted([LEGACY_CURATE.name, SELF_DREAM.name, USER_DREAM.name]),
        )
        curate = next(j for j in backend.jobs if j["name"] == LEGACY_CURATE.name)
        self.assertEqual(curate["id"], "legacy")

    def test_second_reconcile_is_noop(self):
        backend = FakeBackend([
            job_from_spec(USER_DREAM, "u"),
            job_from_spec(SELF_DREAM, "s"),
            job_from_spec(LEGACY_CURATE, "c"),
        ])
        result = reconcile(backend)
        self.assertTrue(result["ok"])
        self.assertEqual(result["actions"], [])

    def test_duplicate_canonical_jobs_are_removed(self):
        backend = FakeBackend([
            job_from_spec(USER_DREAM, "u1"),
            job_from_spec(USER_DREAM, "u2"),
            job_from_spec(SELF_DREAM, "s"),
            job_from_spec(LEGACY_CURATE, "c"),
        ])
        result = reconcile(backend)
        self.assertTrue(result["ok"])
        self.assertEqual(
            len([j for j in backend.jobs if j["name"] == USER_DREAM.name]),
            1,
        )

    def test_no_legacy_curator_removes_old_and_curate_jobs(self):
        backend = FakeBackend([
            job_from_spec(USER_DREAM, "u"),
            job_from_spec(SELF_DREAM, "s"),
            job_from_spec(LEGACY_CURATE, "c"),
            {
                "id": "legacy",
                "name": "lucid:dream",
                "schedule_display": "12 10 * * *",
                "prompt": "old",
                "deliver": "local",
                "enabled": True,
                "state": "scheduled",
                "skills": [],
            },
        ])
        result = reconcile(backend, keep_legacy_curator=False)
        self.assertTrue(result["ok"])
        names = {j["name"] for j in backend.jobs}
        self.assertEqual(names, {USER_DREAM.name, SELF_DREAM.name})


if __name__ == "__main__":
    unittest.main(verbosity=2)
