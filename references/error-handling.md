# Error Handling — Full Reference

The SKILL.md carries a short table of the failures that occur most often. This
file has the full set, including the per-run and self-update paths.

| Failure | Symptom | Handling |
|---------|---------|----------|
| `config.json` missing | Script exits `2` before processing | Run `lucid.init`, then re-run. Do not hand-write a config — the cursor format is load-bearing for resumption. |
| `config.json` unparseable | Script exits `2` with a JSON error | Restore from git or rewrite via `lucid.init`. Never "fix" it by hand-editing the cursor; a wrong cursor re-files or skips journals silently. |
| Source journal is malformed JSON | `read_error` recorded, score `-3`, run continues | Producer-side bug (commonly `ocas-mentor` trailing commas, unescaped newlines in `notes`). File an issue against the producer; do **not** patch the journal in place — the cursor may re-read it and the fix will be overwritten. Preserve the malformed source journal unchanged and file the producer issue. |
| Chronicle ingestion unavailable | Curated artifacts still write normally | Downstream ingestion retries independently; Lucid does not mutate Chronicle directly. |
| Curated artifact write fails | `curated_write_failed` recorded | Do not claim the source was filed; retry during repair/catch-up. |
| Source has no explicit principal | Candidate is omitted | Keep the curated evidence; never infer user ownership. |
| Reference file missing from disk | A section cannot be read | Fall back to the procedural instructions in the SKILL.md body. Do not block the run. |
| Backlog > 1000 journals, batch files nothing interesting | `file_count: 0` across several runs | Cursor is buried in scan-heavy territory. Run a targeted pass over high-signal skills only (vesper, praxis, taste, custodian, dispatch). See "buried backlog" in `references/scoring-traps.md`. |
| `re_evaluations` skips cleanup silently | Recirculation entries never promoted | Use `e.get('re_evaluations') or 0`; a bare `>= 3` against `None` raises `TypeError` in Python 3, not a quiet `False`. |
| Duplicate filed entries | Same content in two drawers | Check `decisions.jsonl` for an existing `file` decision before writing; record `skip`/`already_filed` instead. |
| `update.sh` exits 2 | Unknown argument | Usage error; re-run with `--help`. |
| `update.sh` exits 3 | "worktree has uncommitted changes" | **Refusal, not a failure.** Commit or stash the changes, or pass `--force` to discard them deliberately. |
| `update.sh` exits 4 | Divergence or pull failure | Reconcile manually, or re-run with `--force` to discard local commits. |
| `execute_code` blocked in cron | Tool unavailable in a cron session | Expected. Use `write_file` + `terminal`; see `references/platform-notes.md`. |

## Validation loop

For any change to classification or filing logic: run the template with
`--dry-run` first, confirm the counts and the `file_details` look right, then
commit the batch with a normal run. `--dry-run` is byte-for-byte read-only
across `config.json`, `decisions.jsonl`, `ingestion_log.jsonl`,
`recirculation_queue.jsonl`, and `evidence.jsonl` — this is enforced by
`tests/test_smoke.py`.
