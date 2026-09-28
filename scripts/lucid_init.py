#!/usr/bin/env python3
"""Initialize or migrate Lucid Dreaming cron jobs."""

from __future__ import annotations

import argparse
import json
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
    p.add_argument("--json", action="store_true")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    result = reconcile(
        HermesCronCLI(executable=args.hermes),
        keep_legacy_curator=not args.no_legacy_curator,
    )
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        for action in result["actions"]:
            print(json.dumps(action, sort_keys=True))
        print("Lucid cron reconciliation:", "OK" if result["ok"] else "FAILED")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
