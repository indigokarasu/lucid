"""Lucid cron registration and migration.

Lucid owns the Dreaming schedules. This module uses the Hermes CLI rather than
editing jobs.json directly, so provider notifications, validation, locking,
and next-run computation stay host-owned.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class CronSpec:
    name: str
    schedule: str
    prompt: str
    skill: str = "ocas-lucid"
    deliver: str = "local"


_SKILL_ROOT = Path(__file__).resolve().parent.parent


def _script_command(name: str) -> str:
    return "python3 " + shlex.quote(str(_SKILL_ROOT / "scripts" / name)) + " --json"


USER_DREAM = CronSpec(
    name="lucid:user-dream",
    schedule="20 2 * * *",
    prompt=(
        "Run Lucid User Dreaming. Load the ocas-lucid skill, then execute: "
        + _script_command("lucid_user_dream.py")
        + ". Treat a non-zero exit as a failed cron run and report the error; "
        "otherwise remain silent."
    ),
)

SELF_DREAM = CronSpec(
    name="lucid:self-dream",
    schedule="5 0 * * *",
    prompt=(
        "Run Lucid self-Dreaming. Load the ocas-lucid skill, then execute: "
        + _script_command("lucid_self_dream.py")
        + ". Treat a non-zero exit as a failed cron run and report the error; "
        "otherwise remain silent."
    ),
)

LEGACY_CURATE = CronSpec(
    name="lucid:curate",
    schedule="12 10 * * *",
    prompt=(
        "Run the Lucid legacy curator compatibility cycle only. Load the "
        "ocas-lucid skill and execute: "
        + _script_command("lucid_curate.py")
        + ". Do not run User Dreaming or self-Dreaming from this job."
    ),
)

LEGACY_NAMES = {"lucid:dream"}


class HermesCronCLI:
    """Small adapter around the host-owned Hermes cron CLI."""

    def __init__(self, *, executable: str = "hermes", runner: Callable[..., Any] | None = None):
        self.executable = executable
        self._runner = runner or subprocess.run

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return self._runner(
            [self.executable, "cron", *args],
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def _jobs_path() -> Path:
        home = Path(os.environ.get("HERMES_HOME") or "~/.hermes").expanduser()
        return home / "cron" / "jobs.json"

    def list_jobs(self) -> list[dict[str, Any]]:
        """Read the host registry for identity/status only; never write it."""
        path = self._jobs_path()
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.get("jobs") or [])
        raise ValueError(f"unsupported cron registry shape: {path}")

    def create(self, spec: CronSpec) -> None:
        proc = self._run(
            "create",
            spec.schedule,
            spec.prompt,
            "--name",
            spec.name,
            "--deliver",
            spec.deliver,
            "--skill",
            spec.skill,
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"failed creating {spec.name}")

    def edit(self, job_id: str, spec: CronSpec) -> None:
        proc = self._run(
            "edit",
            job_id,
            "--schedule",
            spec.schedule,
            "--prompt",
            spec.prompt,
            "--name",
            spec.name,
            "--deliver",
            spec.deliver,
            "--skill",
            spec.skill,
        )
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"failed editing {spec.name}")

    def remove(self, job_id: str) -> None:
        proc = self._run("remove", job_id)
        if proc.returncode:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"failed removing {job_id}")


def _schedule_text(job: dict[str, Any]) -> str:
    schedule = job.get("schedule") or {}
    return str(
        job.get("schedule_display")
        or schedule.get("display")
        or schedule.get("expr")
        or ""
    )


def _skills(job: dict[str, Any]) -> list[str]:
    values = list(job.get("skills") or [])
    if job.get("skill") and job["skill"] not in values:
        values.append(job["skill"])
    return values


def matches(job: dict[str, Any], spec: CronSpec) -> bool:
    """Return whether an existing job already implements the desired spec."""
    return (
        job.get("name") == spec.name
        and _schedule_text(job) == spec.schedule
        and str(job.get("deliver") or "local") == spec.deliver
        and spec.skill in _skills(job)
        and str(job.get("prompt") or "") == spec.prompt
        and bool(job.get("enabled", True))
        and str(job.get("state") or "scheduled") not in {"paused", "completed"}
        and job.get("paused_at") in (None, "")
    )


def reconcile(
    backend: HermesCronCLI,
    *,
    keep_legacy_curator: bool = True,
) -> dict[str, Any]:
    """Idempotently reconcile Lucid's required cron jobs."""

    jobs = backend.list_jobs()
    desired = [USER_DREAM, SELF_DREAM]
    if keep_legacy_curator:
        desired.append(LEGACY_CURATE)

    actions: list[dict[str, str]] = []

    legacy_jobs = [j for j in jobs if j.get("name") in LEGACY_NAMES]
    curate_jobs = [j for j in jobs if j.get("name") == LEGACY_CURATE.name]
    if legacy_jobs:
        primary = legacy_jobs[0]
        if keep_legacy_curator and not curate_jobs:
            backend.edit(str(primary["id"]), LEGACY_CURATE)
            actions.append({"action": "migrate", "from": str(primary["id"]), "to": LEGACY_CURATE.name})
        else:
            backend.remove(str(primary["id"]))
            actions.append({"action": "remove", "job": str(primary["id"])})
        for duplicate in legacy_jobs[1:]:
            backend.remove(str(duplicate["id"]))
            actions.append({"action": "remove_duplicate", "job": str(duplicate["id"])})

    jobs = backend.list_jobs()

    for spec in desired:
        existing = [j for j in jobs if j.get("name") == spec.name]
        if not existing:
            backend.create(spec)
            actions.append({"action": "create", "job": spec.name})
            jobs = backend.list_jobs()
            continue

        primary = existing[0]
        if not matches(primary, spec):
            backend.edit(str(primary["id"]), spec)
            actions.append({"action": "edit", "job": spec.name})
        for duplicate in existing[1:]:
            backend.remove(str(duplicate["id"]))
            actions.append({"action": "remove_duplicate", "job": str(duplicate["id"])})

    if not keep_legacy_curator:
        for job in backend.list_jobs():
            if job.get("name") == LEGACY_CURATE.name:
                backend.remove(str(job["id"]))
                actions.append({"action": "remove", "job": str(job["id"])})

    final_jobs = backend.list_jobs()
    status = {
        spec.name: {
            "present": any(j.get("name") == spec.name for j in final_jobs),
            "matching": any(matches(j, spec) for j in final_jobs),
        }
        for spec in desired
    }
    return {
        "actions": actions,
        "desired": sorted(spec.name for spec in desired),
        "status": status,
        "ok": all(v["present"] and v["matching"] for v in status.values()),
    }


def lucid_jobs_status(backend: HermesCronCLI) -> dict[str, Any]:
    jobs = backend.list_jobs()
    names = {USER_DREAM.name, SELF_DREAM.name, LEGACY_CURATE.name, *LEGACY_NAMES}
    relevant = [j for j in jobs if j.get("name") in names]
    return {
        "jobs": [
            {
                "id": j.get("id"),
                "name": j.get("name"),
                "schedule": _schedule_text(j),
                "enabled": j.get("enabled", True),
                "state": j.get("state"),
                "last_run_at": j.get("last_run_at"),
                "last_status": j.get("last_status"),
                "last_error": j.get("last_error"),
                "next_run_at": j.get("next_run_at"),
            }
            for j in relevant
        ]
    }
