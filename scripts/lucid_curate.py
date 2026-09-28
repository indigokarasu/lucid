#!/usr/bin/env python3
"""Compatibility entry point for the legacy Lucid journal curator."""

from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).with_name("lucid_dream_template.py")

if __name__ == "__main__":
    runpy.run_path(str(TARGET), run_name="__main__")
