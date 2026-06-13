# Lucid Gotchas

## Journal Discovery

- **Journal discovery in cron context**: `execute_code` is blocked in cron jobs. Use `terminal(find ...)` with `-newermt` and `-name` filters to enumerate JSON journals, then cross-reference against the ingestion log's processed set. For per-skill latest files: `find /root/.hermes/commons/journals/<skill> -name \"*.json\" -type f -printf '%T@ %p\\n' | sort -rn | head -5`.
- **`search_files` with glob patterns does not reliably find JSON journals nested in date subdirectories** under `{agent_root}/commons/journals/`. Use `terminal(find)` or `execute_code` (interactive only) with `os.walk`.
- **Multiple journal base paths**: Journals exist in BOTH `/root/.hermes/commons/journals/` AND `/root/.hermes/agents/indigo/commons/journals/`. Always search both locations. The commons path is the primary; the profile path may contain additional run-specific files.
- **Full cron shell pipeline for unprocessed journal dedup**: When `execute_code` is blocked, use this pattern to build the unprocessed set:
  ```bash
  # Step 1: Build processed set from ingestion log
  cat /root/.hermes/commons/data/ocas-lucid/ingestion_log.jsonl | \
    python3 -c "
  import json, sys
  for line in sys.stdin:
      line = line.strip()
      if not line: continue
      try:
          e = json.loads(line)
          print(e.get('skill',''), e.get('run_id',''))
      except: pass
  " 2>/dev/null | sort -u > /tmp/processed_pairs.txt

  # Step 2: Add cursor entries
  python3 -c "
  import json
  with open('/root/.hermes/commons/data/ocas-lucid/config.json') as f:
      config = json.load(f)
  cursor = config.get('cursor', {})
  with open('/tmp/processed_pairs.txt', 'a') as out:
      for skill, rids in cursor.items():
          for rid in rids:
              print(skill, rid, file=out)
  "
  sort -u /tmp/processed_pairs.txt > /tmp/processed_pairs_dedup.txt

  # Step 3: Find all journals with skill, filename, mtime
  find /root/.hermes/commons/journals /root/.hermes/agents/indigo/commons/journals \
    -name "*.json" -type f \
    -not -path "*/.archive/*" -not -path "*/.quarantine/*" -not -path "*/staging/*" \
    -not -path "*/test*" \
    -printf '%h %f %T@\n' 2>/dev/null | \
  awk '{ split($1, parts, "/"); skill = parts[6]; if (skill == "") skill = parts[7];
         printf "%s %s %s\n", skill, $2, int($3) }' | sort -k3 -rn > /tmp/all_journals_list.txt

  # Step 4: Filter out processed (set-minus via awk)
  awk 'NR==FNR {processed[$1" "$2]=1; next}
       !processed[$1" "$2] {print}' \
    /tmp/processed_pairs_dedup.txt /tmp/all_journals_list.txt \
    > /tmp/unprocessed_journals.txt

  # Step 5: Take top N newest
  head -40 /tmp/unprocessed_journals.txt
  ```
- **Config cursor merge without duplicates**: When updating the cursor in config.json, load existing lists, merge new run_ids into sets (dedup), then write back. Use `sorted(set(...))` to maintain order. Never append blindly — re-processing already-seen journals wastes the iteration budget.

## Elephas Coordination

- **After running elephas manually**: When the elephas cron pipeline is run manually (because the `ocas-elephas` skill is not installed), the lucid config cursor in `config.json` must be updated to include the new elephas journal files. Add the new `run_cron_*.json` and `journal_ingest_consolidate_*.json` entries to both the `cursor.ocas-elephas` list AND the `cursor.elephas` list. Without this, lucid will try to re-process elephas journals on the next dream cycle.
- **Elephas skill archived but cron jobs active**: The `ocas-elephas` skill exists in `.archive/ocas-elephas-disabled/` but cron jobs still reference it. When the skill is not found, the agent must run the pipeline script directly: `LADYBUG_DB=chronicle python3 /root/.hermes/commons/db/ocas-elephas/elephas_cron_pipeline.py`. See custodian gotcha "Elephas pipeline bridge dependency" for bridge management procedure.

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
- **Queue size monitoring**: If the recirculation queue exceeds 50 entries, run a cleanup pass before processing new journals. Move entries with `re_evaluations >= 3` or entries older than 30 days (by `added_at`) to `removed_entries.jsonl`. Log the cleanup count in the dream journal. A bloated queue slows down every run and indicates systemic classification issues that need addressing.

## Missing Reference Files

- **Support files may be absent**. `dream-cycle.md`, `re-emergence.md`, `safety-gates.md`, and `dream-journal.md` are referenced in the Support File Map but may not exist on disk. When a reference file is missing, fall back to the procedural instructions in the SKILL.md body itself. The SKILL.md is the authoritative source; references are supplements, not requirements. Log a note in the dream journal if a reference file was expected but missing, but do not block the run.

## Tool Path Resolution

- **`read_file` may fail with "File not found" for paths under `/root/.hermes/` even when the file exists.** The tool sometimes prepends the profile home directory to absolute paths. When `read_file` fails on an absolute path, retry with `terminal(cat <path>)` or `terminal(find ...)` as a fallback. This is especially common for files under `/root/.hermes/skills/`, `/root/.hermes/commons/`, and `/root/.hermes/agents/`.
- **`execute_code` is blocked in cron context.** Use `terminal()` with heredoc Python for any multi-step file processing. Keep terminal commands under the timeout limit (default 180s); for large operations, break into separate calls.

## Journal Field Diversity Across Skills

**Narrative content lives in different field paths depending on the skill.** Do NOT assume all journals use the `decision.summary` / `decision.reasoning_summary` fields. Known field paths by skill:

| Skill | Narrative fields (in priority order) |
|-------|--------------------------------------|
| ocas-mentor (light) | No narrative — metrics only (`metrics.*`, `outcome`). Always scores -3. Skip without reading body. |
| ocas-custodian (light-scan) | `findings.*.description` (findings dict values). Usually routine — apply routine_health_check penalty. |
| ocas-custodian (deep) | `findings.*.description` with rich diagnostic content. Score normally. |
| ocas-forge (journal-scan) | `result.action_taken` (string). Low scores unless proposals found. |
| ocas-praxis (debrief) | `summary` (top-level string describing shifts/events). |
| ocas-rally | `decision` (top-level string), `rationale` (string), `events_observed[]` (list). Rich content. |
| ocas-dispatch | `decision.reasoning_summary`, `decision.payload.reason` (string). |
| ocas-spot | `results.*.note` (per-venue notes with operational detail). |
| ocas-weave | `decision.reasoning_summary`, `decision.payload` values. |
| ocas-elephas | `decision.payload` values (not keys). Usually low narrative. |
| ocas-taste | `decision.reasoning_summary`, `fixes_applied[]` (top-level array of fix descriptions), `summary` (top-level). The `fixes_applied` field is a high-value narrative source — each entry describes a concrete code/config fix and should be included in scoring text. |
| ocas-bones (assessment) | `summary` (top-level) or `findings.*.description`. Assessment runs may have no narrative — skip quickly after checking `summary`. |

When classifying, walk a **search-order list** of possible narrative locations rather than assuming the standard JournalEntry schema. Extract from: (1) `decision.summary`, `decision.reasoning_summary`, `decision.description`, (2) `summary` (top-level), (3) `rationale`, (4) `findings.*.description`, (5) `results.*.note`, (6) `events_observed[]`, (7) `decision` if it's a plain string. Stop at the first set of fields that yields >20 chars of narrative.

## Backlog Management

- **Backlog can grow very large** (5000+ unprocessed journals). The catch-up cap of 40 journals/run means clearing a large backlog takes 125+ runs. Prioritize quality over quantity — a correct classification that skips 40 noise journals is more valuable than a rushed one that files noise.
- **If backlog exceeds 1000**, consider whether the classification thresholds are too aggressive. A healthy system should see ~10-20% of journals score file-worthy over time. If nearly everything scores -3 to 0, the scraping surface may be pulling too many routine operational journals — consider filtering by filename pattern (e.g., skip `*-light-*` and `*-scan-*` journals) to reduce processing load.
- **Do not attempt to clear the entire backlog in one run.** The 40-journal cap exists to prevent timeout. Trust the incremental approach.

## Recirculation Queue `re_evaluations` Field

- **`re_evaluations` can be `null` (not 0)** in older queue entries. Always use `e.get('re_evaluations') or 0` when comparing. Direct `>= 3` comparison against `null` returns `False` in Python and silently skips cleanup.

### Payload keys vs. narrative content

The `correction_or_lesson(+4)` signal must ONLY fire on narrative text fields (`summary`, `description`, `reasoning_summary`). Do NOT count payload dictionary **key names** (like `lessons_extracted`) as content — this causes routine operational journals to score 6+ and get filed as noise. Apply keyword checks to the extracted narrative text only, not to the full serialized JSON.

### Count-summary false positive

A variant of the payload-key trap: some journals (especially praxis ingest reports) embed metric counts in their `decision.summary` string, e.g. `"Ingest complete: 7 journals scanned, 1 new events, 9 new lessons, 0 shifts activated"`. The word "lessons" here is a **count**, not a narrative lesson. Before firing `correction_or_lesson(+4)`, check whether the matched word appears in a count-summary context (pattern: `"N new <word>"`, `"<word>: N"`, or at the start of a summary line that is purely numeric/metric). If so, skip the signal. This prevents routine ingest reports from scoring 4+ and entering recirculation.
