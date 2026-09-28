#!/usr/bin/env python3
"""Report Lucid Dreaming state and cron status."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.cron import HermesCronCLI, lucid_jobs_status
from dreaming.runtime import DreamScope


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Report Lucid status")
    p.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME", "~/.hermes"))
    p.add_argument("--profile", default=os.environ.get("HERMES_PROFILE", "indigo"))
    p.add_argument("--user-principal", default=os.environ.get("LUCID_USER_PRINCIPAL"))
    p.add_argument("--agent-principal", default=os.environ.get("LUCID_AGENT_PRINCIPAL"))
    p.add_argument("--json", action="store_true")
    return p


def _state(home: str, profile: str, principal: str | None, domain: str):
    if not principal:
        return None
    scope = DreamScope.from_values(
        hermes_home=home,
        profile_id=profile,
        principal_id=principal,
    )
    kernel = scope.kernel(domain)
    value = kernel.store.load(kernel.domain)
    runs = value.get("runs") or []
    return {
        "principal_id": principal,
        "domain": domain,
        "active_count": len(value.get("active") or {}),
        "candidate_count": len(value.get("candidates") or {}),
        "last_run": runs[-1] if runs else None,
    }


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    payload = {
        "cron": lucid_jobs_status(HermesCronCLI()),
        "user": _state(args.hermes_home, args.profile, args.user_principal, "relationship"),
        "self": _state(args.hermes_home, args.profile, args.agent_principal, "self"),
    }
    print(json.dumps(payload, indent=None if args.json else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
