# Cron Execution Detail

Expanded operational detail for running the dream cycle from cron. The SKILL.md
body carries the decision-level rules; this file carries the per-flag
classification exceptions, the sort order, and the degraded-mode tree.

## Cron pattern

> **Critical**: `execute_code` is **blocked** in cron mode. Use `write_file` to
> write a Python script to `/tmp/`, then invoke it via
> `terminal(command="python3 /tmp/script.py")`.

The bundled template already implements all of the below. Copy it to `/tmp/`
and adapt rather than writing a cycle from scratch:

```bash
cp <skill_dir>/scripts/lucid_dream_template.py /tmp/lucid_dream.py
python3 /tmp/lucid_dream.py --help        # usage, no side effects
python3 /tmp/lucid_dream.py --dry-run     # classify + print, write nothing
python3 /tmp/lucid_dream.py --json        # machine-readable run summary
```

Flags: `--batch-size N` (default 200), `--dry-run`, `--json`.
Exit codes: `0` completed/help, `2` bad usage or `config.json` missing.

## Multi-batch processing (large backlogs)

When the backlog exceeds ~500 files (common), a 40-journal batch is entirely
consumed by scan files. **Default to `BATCH_SIZE = 200`** (the template's
default) to process 5x more per run and reach interesting signals sooner.
Use `--batch-size 40` for a conservative pass when the goal is depth over
backlog clearing.

## Two-pass classification workflow

**First run (no cursor)**: Alphabetical sorting places scan/sweep journals
(forge, finch, custodian) before interesting journals (mentor, praxis, dispatch,
vesper, taste). A batch cap means the first batch may be *entirely* scan files.

1. Separate journals into "interesting" and "scan" using `is_scan()` with
   **skill-level exceptions** — `mentor-light`, `vesper`, `taste`,
   `praxis-review`, `dispatch-triage` are NEVER scans
2. Sort interesting journals by **skill priority** (below) — NOT alphabetically
3. Process interesting journals first (up to the cap)
4. Track both groups in the cursor; remaining scans process in later runs

**Subsequent runs**: Resume from cursor, process next batch. Once all
interesting journals are processed, move to scan batches.

## Journal priority heuristic

Sort key: `(is_scan, skill_priority, filename)`.

High-signal skills first:

| Priority | Skill | Signal |
|----------|-------|--------|
| 0 | `ocas-mentor` | evaluation coverage, behavioral corrections in `notes` |
| 1 | `ocas-vesper` | `*morning*` / `*evening*` briefings; `notes` field |
| 2 | `ocas-praxis` | `praxis-review-*`, `praxis-debrief*`; `reasoning_summary` or `notes` |
| 3 | `ocas-taste` | consumption pattern records |
| 4 | `ocas-dispatch` | `dispatch-triage-*`, `dispatch-draft-*`; `reasoning_summary` |
| 5 | `ocas-spot` | `spot-*` files are interesting, not scans |
| 6 | `ocas-forge` | mostly `journal-scan-*` / numeric `r_*` |
| 7 | `ocas-custodian` | `light-scan-*` interesting from ~June 14 (lesson/blocker content, scores 6-7); `deep-scan-*` not |

Almost-exclusively scan content (skip unless the cap allows):
`ocas-finch` (`scan-*`, `daily-*`, `weekly-*`), `ocas-spot` (`sweep-*`,
`spot-watch-*`), `ocas-custodian` (`deep-scan-*`).

## Curation and downstream-ingestion decision tree

1. Classify the source journal and preserve its source path/provenance.
2. Write the curated Lucid journal artifact for every `file` classification.
3. If the source explicitly carries a principal, attach a principal-scoped memory candidate.
4. If no principal is explicit, attach no candidate; keep the artifact as evidence only.
5. Chronicle availability is not a Lucid precondition. Durable ingestion is a separate downstream concern.
6. If the curated artifact cannot be written, record the failure and leave the source eligible for repair/retry.

## Cron-specific environment constraints

- `execute_code` is blocked in cron jobs — use `write_file` + `terminal`.
  See `references/platform-notes.md`.
- The `memory` tool may be unavailable in cron context. If memory writes fail,
  skip them: the skill's own data files (ingestion log, decisions, evidence,
  config) are the durable store. Memory is a convenience layer.
- Cron sessions have a lighter toolset than interactive ones. Check tool
  availability before assuming a tool exists.
- No heartbeat entry. Lucid needs one substantial batch run per day, not
  lightweight polling.
