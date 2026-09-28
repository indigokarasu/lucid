#!/usr/bin/env python3
"""Run Lucid User Dreaming against Chronicle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.chronicle import (
    ChronicleDreamWriter,
    ChroniclePatternSource,
    load_chronicle_core,
    resolve_user_principal,
)
from dreaming.runtime import DreamScope
from dreaming.user import UserDreamRunner


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Lucid User Dreaming")
    p.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME", "~/.hermes"))
    p.add_argument("--profile", default=os.environ.get("HERMES_PROFILE", "indigo"))
    p.add_argument("--principal", default=os.environ.get("LUCID_USER_PRINCIPAL"))
    p.add_argument("--since-seq", type=int)
    p.add_argument("--limit", type=int, default=5000)
    p.add_argument("--json", action="store_true")
    return p


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    core = load_chronicle_core(args.hermes_home)
    principal = resolve_user_principal(core, args.principal)
    scope = DreamScope.from_values(
        hermes_home=args.hermes_home,
        profile_id=args.profile,
        principal_id=principal,
    )
    kernel = scope.kernel("relationship")
    state = kernel.store.load(kernel.domain)
    if args.since_seq is None:
        runs = state.get("runs") or []
        since_seq = max((int(r.get("last_seq") or 0) for r in runs), default=0)
    else:
        since_seq = args.since_seq

    source = ChroniclePatternSource(core, principal_id=principal)
    writer = ChronicleDreamWriter(core, principal_id=principal)
    result = UserDreamRunner(
        principal_id=principal,
        kernel=kernel,
        source=source,
        writer=writer,
    ).run(since_seq=since_seq, limit=args.limit)

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "Lucid User Dreaming: "
            f"seen={payload['seen_patterns']} proposed={payload['proposed']} "
            f"promoted={payload['promoted']} held={payload['held']} "
            f"blocked={payload['blocked']} last_seq={payload['last_seq']}"
        )
        if payload["errors"]:
            for error in payload["errors"]:
                print(f"ERROR: {error}")
    return 0 if not payload["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
