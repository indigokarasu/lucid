# Changelog

## [3.0.2] — 2026-11-01

### Added
- `tests/test_smoke.py` (5 tests: frontmatter, metadata, triggers, sections, references)
- `.github/workflows/ci.yml` for automated testing
- "Why" explanations for all scoring signals and thresholds (D6)
- Expanded support file map with CHANGELOG, config.json, activity_model.jsonl, degraded-mode-execution (D8)

### Changed
- Scoring signals table now includes a "Why" column explaining each weight
- Thresholds now have per-level rationale

### Fixed
- D6: rigid rules lacked "why" explanations
- D8: support file map was incomplete; added missing entries
- D9: no tests or CI (N/A → 5/5)

### Added
- Nightly journal curation pipeline (Orient → Gather → Classify → Write)
- Relevance scoring signals with thresholds (≥5 write, 3–4 recirculate, ≤2 skip)
- Error handling for corrupt journals, missing cursor, score ties, hibernation
- Self-update procedure: FF-only pull, clean tree requirement, schema validation, rollback
- Support file map with conditional "When to read" signals

### Changed
- None

### Fixed
- None
