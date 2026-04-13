#!/usr/bin/env python3
"""
Lucid initialization script.
Creates storage directories and registers the nightly cron job.
"""

import os
import json
from pathlib import Path

def init():
    agent_root = Path(os.environ.get("AGENT_ROOT", "/root/.hermes"))
    
    # Directories
    journals_dir = agent_root / "commons" / "journals" / "ocas-lucid" / "today"
    data_dir = agent_root / "commons" / "data" / "ocas-lucid"
    
    journals_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Empty log files
    ingestion_log = data_dir / "ingestion_log.jsonl"
    decisions_log = data_dir / "decisions.jsonl"
    
    if not ingestion_log.exists():
        ingestion_log.touch()
    if not decisions_log.exists():
        decisions_log.touch()
    
    print(f"Lucid initialized at {agent_root}")

if __name__ == "__main__":
    init()
