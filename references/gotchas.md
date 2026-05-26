# Lucid Gotchas

## Journal Discovery

- **Journal discovery requires `os.walk`**: `search_files` with glob patterns does not reliably find JSON journals nested in date subdirectories under `{agent_root}/commons/journals/`. Use `execute_code` with `os.walk` to enumerate all `.json` files across skill directories, then cross-reference against the ingestion log's processed set.

## MemPalace KG Triples

- **`mempalace_kg_add` rejects special characters**: The `subject`, `predicate`, and `object` fields in KG triples cannot contain `/`, `#`, `:`, parentheses, or brackets. Sanitize all values before calling — replace slashes with "and", colons with hyphens, strip parentheses. Retry with cleaned text rather than skipping on failure.

## Journal Parsing

- **Journal fields may be null**: Some journals have `None` for string fields (`reasoning_summary`, `decision.description`, etc.). Always coalesce to empty string before calling `.strip()` or string operations.

## Ingestion Log

- **Ingestion log format varies**: Older entries use `{skill, run_id, timestamp, action}` format; newer entries use `{run_id, skill, journal, processed_at, score, filing}`. Both identify journals by `(skill, run_id)` tuple — check both formats when building the processed set.
- **Cursor resumption from two sources**: Build the processed-journal set from both `config.json` cursor AND `ingestion_log.jsonl`. The cursor only tracks the last batch's files, while the ingestion log has the full history. Missing this causes re-processing.
- **Path normalization for dedup**: The cursor may store nested paths like `ocas-vesper/ocas-vesper/2026-04-10/file.json`. Use only the filename portion as the dedup key, or normalize by stripping duplicate directory segments.

## Recirculation Queue

- **Datetime timezone consistency**: When comparing recirculation queue timestamps against current time, ensure both are either offset-aware or offset-naive. Use `datetime.now(timezone.utc)` for offset-aware comparisons.
- **Recirculation queue field name variance**: Older entries may use `skipped_at` vs `added_at` or lack a timestamp entirely. Use `.get()` with defaults; treat missing-timestamp entries as due for re-evaluation.
