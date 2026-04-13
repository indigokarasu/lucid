#!/bin/bash
# Lucid nightly cron handler — runs dream loop in background to avoid timeout

cd ~/.hermes/skills/ocas-lucid
python3 REFERENCES/dream-loop.py
