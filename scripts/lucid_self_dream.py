#!/usr/bin/env python3
"""Run Lucid self-Dreaming on the latest Autobio observation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from dreaming.chronicle import load_chronicle_core, resolve_agent_principal
from dreaming.runtime import DreamScope
from dreaming.self import SelfDreamRunner


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run Lucid self-Dreaming")
    p.add_argument("--hermes-home", default=os.environ.get("HERMES_HOME", "~/.hermes"))
    p.add_argument("--profile", default=os.environ.get("HERMES_PROFILE", "indigo"))
    p.add_argument("--principal", default=os.environ.get("LUCID_AGENT_PRINCIPAL"))
    p.add_argument(
        "--observations-dir",
        default=os.environ.get("AUTOBIO_OBSERVATIONS_DIR", "/indigokarasu/SOUL/autobio/observations"),
    )
    p.add_argument("--observation")
    p.add_argument("--json", action="store_true")
    return p


def latest_observation(directory: str) -> Path:
    root = Path(directory).expanduser().resolve()
    candidates = sorted(p for p in root.glob("*.md") if p.is_file())
    if not candidates:
        raise FileNotFoundError(f"no Autobio observations found in {root}")
    return candidates[-1]


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    core = load_chronicle_core(args.hermes_home)
    principal = resolve_agent_principal(core, args.principal)
    scope = DreamScope.from_values(
        hermes_home=args.hermes_home,
        profile_id=args.profile,
        principal_id=principal,
    )
    kernel = scope.kernel("self")
    observation = (
        Path(args.observation).expanduser().resolve()
        if args.observation
        else latest_observation(args.observations_dir)
    )
    result = SelfDreamRunner(
        principal_id=principal,
        kernel=kernel,
    ).run_file(observation)

    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(
            "Lucid self-Dreaming: "
            f"source={payload['source_path']} promoted={payload['promoted']} "
            f"held={payload['held']} blocked={payload['blocked']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
