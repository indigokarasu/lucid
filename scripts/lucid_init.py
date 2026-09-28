#!/usr/bin/env python3
"""Initialize or migrate Lucid Dreaming cron jobs."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.cron import HermesCronCLI, reconcile


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Initialize Lucid Dreaming schedules")
    p.add_argument(
        "--no-legacy-curator",
        action="store_true",
        help="Remove the legacy journal-curation job instead of keeping it.",
    )
    p.add_argument("--hermes", default="hermes", help="Hermes CLI executable")
    p.add_argument(
        "--hermes-home",
        default=os.environ.get("HERMES_HOME", "~/.hermes"),
        help="Hermes home used for Lucid state initialization.",
    )
    p.add_argument(
        "--profile",
        default=os.environ.get("HERMES_PROFILE", "indigo"),
        help="Active Hermes profile identifier.",
    )
    p.add_argument("--json", action="store_true")
    return p


def initialize_state(hermes_home: str, profile: str, *, keep_legacy_curator: bool) -> dict:
    home = Path(hermes_home).expanduser().resolve()
    profile_id = str(profile or "").strip()
    if not profile_id or "/" in profile_id or ".." in profile_id:
        raise ValueError("profile must be a simple identifier")

    dream_root = (
        home
        / "commons"
        / "data"
        / "dreaming"
        / "profiles"
        / profile_id
        / "principals"
    )
    dream_root.mkdir(parents=True, exist_ok=True)

    created = []
    if keep_legacy_curator:
        legacy_data = home / "commons" / "data" / "ocas-lucid"
        legacy_journals = home / "commons" / "journals" / "ocas-lucid"
        legacy_data.mkdir(parents=True, exist_ok=True)
        legacy_journals.mkdir(parents=True, exist_ok=True)
        (legacy_data / "staging").mkdir(parents=True, exist_ok=True)

        config = legacy_data / "config.json"
        if not config.exists():
            config.write_text(
                json.dumps(
                    {
                        "schema_version": "4.2",
                        "cursor": None,
                        "cursor_file": None,
                        "last_run": None,
                        "last_run_status": None,
                        "streak": 0,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            created.append(str(config))

        for name in (
            "ingestion_log.jsonl",
            "decisions.jsonl",
            "recirculation_queue.jsonl",
            "removed_entries.jsonl",
            "intents.jsonl",
            "evidence.jsonl",
        ):
            path = legacy_data / name
            if not path.exists():
                path.touch()
                created.append(str(path))

    return {
        "dreaming_root": str(dream_root),
        "created": created,
    }


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    state = initialize_state(
        args.hermes_home,
        args.profile,
        keep_legacy_curator=not args.no_legacy_curator,
    )
    result = reconcile(
        HermesCronCLI(executable=args.hermes, hermes_home=args.hermes_home),
        keep_legacy_curator=not args.no_legacy_curator,
    )
    result["state"] = state
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for action in result["actions"]:
            print(json.dumps(action, sort_keys=True))
        print("Lucid cron reconciliation:", "OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
