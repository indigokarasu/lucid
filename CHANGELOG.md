# Changelog

## [3.0.1] — current

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
