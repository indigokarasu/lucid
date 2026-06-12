# Lucid Gotchas

## Journal Discovery

- **Journal discovery in cron context**: `execute_code` is blocked in cron jobs. Use `terminal(find ...)` with `-newermt` and `-name` filters to enumerate JSON journals, then cross-reference against the ingestion log's processed set. For per-skill latest files: `find /root/.hermes/commons/journals/<skill> -name "*.json" -type f -printf '%T@ %p\n' | sort -rn | head -5`.
- **`search_files` with glob patterns does not reliably find JSON journals nested in date subdirectories** under `{agent_root}/commons/journals/`. Use `terminal(find)` or `execute_code` (interactive only) with `os.walk`.

## MemPalace MCP Tool Availability

- **MemPalace MCP tools may not be in the agent toolset**. Before Phase 4, check whether `mempalace_add_drawer`, `mempalace_kg_add`, `mempalace_check_duplicate`, `mempalace_search`, `mempalace_status`, and `mempalace_get_taxonomy` are available. If none are present, enter degraded mode: complete classification, update all local state files (ingestion_log, decisions, recirculation_queue, config cursor), write the dream journal with `degraded: mempalace` notation, and list the journals that *would* be filed with their wing/room assignments. Do NOT attempt to call tools that aren't in the toolset.
- **Degraded mode is not an error**. Classification and local state updates are still valuable work. The dream journal should clearly state which tools were missing and list the filing decisions that would have been made.

## MemPalace KG Triples

- **`mempalace_kg_add` rejects special characters**: The `subject`, `predicate`, and `object` fields in KG triples cannot contain `/`, `#`, `:`, parentheses, or brackets. Sanitize all values before calling — replace slashes with "and", colons with hyphens, strip parentheses. Retry with cleaned text rather than skipping on failure.
- **Actually call `mempalace_kg_add` during the File phase.** It is NOT sufficient to only file drawers. If a journal produced KG triples in the classification phase, those triples must be written during Phase 4. Skipping KG writes silently loses relationship data.

## Journal Parsing

- **Journal fields may be null**: Some journals have `None` for string fields (`reasoning_summary`, `decision.description`, etc.). Always coalesce to empty string before calling `.strip()` or string operations.
- **Payload-dict scoring trap**: Many skills report payload fields like `lessons_extracted: 3` or `events_recorded: 7`. The word "lesson" in a *payload key* should NOT trigger the `correction_or_lesson(+4)` signal — only the narrative text in `reasoning_summary`, `summary`, or `description` fields should. Counting payload key names as content causes routine operational journals to score 6+ and get filed as noise.

## MemPalace Wing Reality

- **`mempalace_get_taxonomy` and `mempalace_list_wings` may return only `root`** even when `classification.md` defines wings like `wing_research`, `wing_knowledge`, etc. MemPalace MCP does not currently support creating custom wings. When only `root` exists, file into `root` using the wing mapping's room name as the actual room slug (e.g., `root/preferences`, `root/operations`, `root/evolution`). Do NOT attempt to create non-existent wings — the MCP calls will fail silently or return errors.

## Ingestion Log

- **Ingestion log format varies**: Older entries use `{skill, run_id, timestamp, action}` format; newer entries use `{run_id, skill, journal, processed_at, score, filing}`. Both identify journals by `(skill, run_id)` tuple — check both formats when building the processed set.
- **Cursor resumption from two sources**: Build the processed-journal set from both `config.json` cursor AND `ingestion_log.jsonl`. The cursor only tracks the last batch's files, while the ingestion log has the full history. Missing this causes re-processing.
- **Path normalization for dedup**: The cursor may store nested paths like `ocas-vesper/ocas-vesper/2026-04-10/file.json`. Use only the filename portion as the dedup key, or normalize by stripping duplicate directory segments.

## Recirculation Queue

- **Datetime timezone consistency**: When comparing recirculation queue timestamps against current time, ensure both are either offset-aware or offset-naive. Use `datetime.now(timezone.utc)` for offset-aware comparisons.
- **Recirculation queue field name variance**: Older entries may use `skipped_at` vs `added_at` or lack a timestamp entirely. Use `.get()` with defaults; treat missing-timestamp entries as due for re-evaluation.
- **Clean up permanently stale entries**: Entries that have been recirculated for 3+ consecutive cycles without promotion to "file" should be moved to `removed_entries.jsonl` and removed from the queue. Accumulating stale entries wastes re-evaluation budget every run. A recirculation queue entry that stays at score 3-4 across multiple runs without cross-reference boost is unlikely to ever promote — archive it.

## Missing Reference Files

- **Support files may be absent**. `dream-cycle.md`, `re-emergence.md`, `safety-gates.md`, and `dream-journal.md` are referenced in the Support File Map but may not exist on disk. When a reference file is missing, fall back to the procedural instructions in the SKILL.md body itself. The SKILL.md is the authoritative source; references are supplements, not requirements. Log a note in the dream journal if a reference file was expected but missing, but do not block the run.
