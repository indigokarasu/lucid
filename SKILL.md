---
name: ocas-lucid
license: MIT
description: 'Nightly journal curator. Batch-processes OCAS skill journals via relevance
  classification and writes curated content to journal files for the configured memory
  provider to ingest. Classifies each journal for filing as a verbatim journal note,
  structured entity/relationship data, or skip. Features re-emergence detection,
  two-pass stale handling, change magnitude gates, hibernation protection,
  and incremental cursor-based resumption. NOT for real-time memory filing,
  skill evaluation, behavioral pattern detection, or entity identity resolution.'
source: https://github.com/<agent-handle>/lucid
includes:
- references/**
- scripts/**
triggers:
- lucid.dream
- lucid.status
- lucid.init
- lucid.update
metadata:
  author: Indigo Karasu (indigokarasu)
  version: "3.3.0"
  hermes:
    tags:
    - journaling
    - curation
    - memory
    - nightly-cron
    - ocas
    category: infrastructure
---

# Lucid

Nightly journal curator. Batch-processes journals from all OCAS skills, classifies them
by relevance, and writes curated content to Lucid's journal files. The configured memory
provider reads these journals during its ingestion cycle and decides what to persist.

Lucid does NOT depend on any specific memory provider. It writes to
`{agent_root}/commons/journals/ocas-lucid/` and lets the memory provider handle ingestion.

## Interactive Menu

When invoked interactively, present a two-level menu. See `references/interactive-menu.md` for the full menu structure.

## When to Use

- Scheduled nightly cron at 3am (primary mode)
- Manual invocation via `lucid.dream` for immediate processing
- `lucid.status` to check last run, pending journals, filing stats

## When NOT to Use

- Real-time memory filing during active sessions
- Skill evaluation or improvement proposals (Mentor)
- Behavioral pattern detection (Corvus)
- Entity identity resolution (Elephas)
- Inspecting a single known journal (just read the file)

## Dream cycle checklist

Run in order; do not skip a phase — each journal is processed to completion
(file + cursor advance) before the next, so a mid-run kill loses at most the
dream journal summary.

- [ ] **Orient** — load `config.json`; build the processed set from
      `ingestion_log.jsonl`; check for a >24h gap and run catch-up if needed
- [ ] **Gather** — discover unprocessed journals; sort by
      `(is_scan, skill_priority, filename)`; cap at `--batch-size` (default 200)
- [ ] **Classify** — extract narrative text (multi-path, not top-level only),
      score, assign taxonomy room; apply safety gates before filing
- [ ] **File** — check `decisions.jsonl` for an existing `file` decision on the
      source path first; if already filed, record `skip`/`already_filed` rather
      than writing a duplicate
- [ ] **Close out** — append decisions + ingestion log + recirculation entries;
      write the dream journal; append evidence; advance `config.json` cursor,
      streak, and counters

## Initialization checklist

- [ ] Create `{agent_root}/commons/data/ocas-lucid/` and `staging/`
- [ ] Write default `config.json` with ConfigBase fields and skill-specific defaults
- [ ] Create empty `ingestion_log.jsonl`, `decisions.jsonl`,
      `recirculation_queue.jsonl`, `removed_entries.jsonl`
- [ ] Create `{agent_root}/commons/journals/ocas-lucid/`
- [ ] Register cron jobs `lucid:dream` and `lucid:update` — **check before
      registering** (why: re-registering duplicates the job and double-runs the
      cycle, corrupting the cursor)
- [ ] Log initialization as a DecisionRecord

## Error handling

| Failure | Symptom | Handling |
|---------|---------|----------|
| `config.json` missing | Script exits `2` before processing | Run `lucid.init`, then re-run. Do not hand-write a config — the cursor format is load-bearing for resumption. |
| Source journal is malformed JSON | `read_error` recorded, score `-3`, run continues | Producer-side bug (commonly `ocas-mentor`). Do not patch the journal in place — the cursor will re-read it and the fix will be overwritten. |
| MemPalace MCP unavailable | `degraded: mempalace` in evidence, `filed_count: 0` | **Expected, not fatal.** Decisions, ingestion log, and dream journal are still written. Filing is retried next run. |
| MemPalace errors mid-batch | Per-call error logged, remaining journals continue | Queue for retry; never abort the batch — a partial run still advances the cursor usefully. |
| Backlog > 1000 journals, batch files nothing | `file_count: 0` across several runs | Cursor is buried in scan-heavy territory. Run a targeted pass over high-signal skills only (vesper, praxis, taste, custodian, dispatch). |
| `update.sh` exits 3 | "worktree has uncommitted changes" | **Refusal, not a failure.** Commit or stash, or pass `--force` to discard deliberately. |

Full table — including duplicate-filing, wing-fallback, and divergence cases —
in `references/error-handling.md`.

## Responsibility boundary

Lucid owns nightly journal scanning, MemPalace filing, relevance
classification, recirculation, and re-emergence. It does **not** own Chronicle
writes (Elephas), social graph updates (Weave), real-time pattern analysis
(Corvus), skill evaluation (Mentor), or entity identity resolution (Elephas).

Read `references/boundaries-and-interfaces.md` when deciding which skill should
handle a task, when Elephas is run manually (update the `config.json` cursor to
avoid double-filing), or when wiring a new consumer of Lucid's output.

## Commands

- `lucid.dream` -- run the full dream cycle immediately, ignoring the time gate
- `lucid.status` -- last run timestamp, journals pending, cumulative filing stats
- `lucid.init` -- create storage directories, initialize config and logs, register cron jobs
- `lucid.update` -- pull latest from GitHub source; preserves journals and data

### Bundled scripts

| Script | Usage | Exit codes |
|--------|-------|-----------|
| `scripts/lucid_dream_template.py` | `--help`, `--dry-run`, `--batch-size N`, `--json` | 0 completed/help, 2 bad usage or missing `config.json` |
| `scripts/update.sh` | `--help`, `--dry-run`, `--force` | 0 updated, 2 bad usage, 3 dirty worktree (refused), 4 divergence/pull failure |

Both scripts are safe to invoke with `--help`: they print usage and exit 0
without touching journal, log, or config state. Use `--dry-run` on the dream
cycle to preview a batch before it advances the cursor.

## Recovery behavior

Implements the recovery contract from `spec-ocas-recovery.md`: an evidence
record on every cycle (including skip/hibernation runs), >24h gap detection
with a capped catch-up pass, degraded mode when MemPalace is unavailable, and
30/90-day log compaction.

See `references/recovery-and-scheduling.md` for the full contract, the cron
job table, schedule-gap recovery, and the OKR evaluation table.

## Storage layout

```
{agent_root}/commons/data/ocas-lucid/
  config.json
  ingestion_log.jsonl
  decisions.jsonl
  recirculation_queue.jsonl
  removed_entries.jsonl
  staging/
  intents.jsonl
  evidence.jsonl

{agent_root}/commons/journals/ocas-lucid/
  YYYY-MM-DD/
    {run_id}.json
```

### I/O examples

**Evidence record** (one line appended to `evidence.jsonl` per cycle, including
skip and hibernation runs — `not_activity_reason` is mandatory when no side
effects occur):

```json
{"timestamp": "2026-09-26T03:00:12+00:00", "run_id": "dream-20260926T030012Z",
 "dream_cycle": true, "mode": "cron", "journals_scanned": 200,
 "total_journals": 11452, "file_count": 3, "recirculate_count": 1,
 "skip_count": 196, "filed_count": 3, "not_activity_reason": null}
```

**Ingestion log entry** (the authoritative processed-set; the `file` key is
what cursor resumption matches on):

```json
{"run_id": "dream-20260926T030012Z",
 "file": "/root/.hermes/commons/journals/ocas-mentor/2026-08-09/mentor-light-20260809T113119Z.json",
 "processed_at": "2026-09-26T03:00:12+00:00", "classification": "skip", "score": 2}
```

**Dream journal** — `{journals}/ocas-lucid/2026-09-26/dream-20260926T030012Z.json`,
`journal_spec_version "1.3"`, `type: "Action"` (MemPalace writes are external
side effects). Carries the same counters plus `file_details`,
`recirculate_details`, `skip_details`, `re_emergence_events`, and
`signal_emissions`. Full schema in `references/dream-journal.md`.

## Initialization

Run the **Initialization checklist** above on `lucid.init` or first invocation.

## Dream cycle pipeline

Four phases executed sequentially. Each journal is processed to completion
(file + cursor advance) before moving to the next, so a mid-run termination
loses no filed work. See `references/dream-cycle.md` for the full phase-by-phase
procedure (Orient, Gather, Classify, File), cursor tracking, and filing
pitfalls.

### Incremental cursor

The ingestion log tracks each processed run_id. If the session terminates mid-run, the next cycle resumes from the first unprocessed journal. Filed content and cursor updates are durable — only the dream journal summary is lost on interruption.

## Re-emergence detection & stale handling

See `references/re-emergence.md` for the full re-emergence algorithm (3+ journal threshold, auto-promotion) and two-pass stale handling (mark on first contradiction, invalidate on second confirmation).

## Safety gates

See `references/safety-gates.md` for change magnitude gates (>30% warning, >50% staging hold) and hibernation protection (7-day no-new-journals → skip with zero IO).

**Why these gates are rigid**: a filing decision that would rewrite more than
half the indexed content is far more likely to be a misclassification than a
genuine change, and an unrecoverable MemPalace write is the expensive failure.
Hibernation exists so a quiet night produces an explicit "no activity" record
rather than an empty journal that later reads as a failed run.

## Dream journal output

Journal type: Action (writes to MemPalace are external side effects). Written to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json` using the standard JournalEntry schema with `journal_spec_version "1.3"`.

See `references/dream-journal.md` for the full journal schema (scan/file/skip counts, re-emergence events, Signal payload, skip path).

## OKR evaluation

Universal OKRs per `spec-ocas-journal.md`, plus skill-specific targets. See `references/okr.md` for the full OKR table (ingestion coverage, duplicate avoidance, recirculation, Signal precision, schedule adherence, data integrity).

## Inter-skill interfaces

Reads all skill journals from `{agent_root}/commons/journals/` (read-only);
writes MemPalace drawers/KG via MCP, the Signal payload in its own dream
journal, and its own data files. Full read/write/query surface in
`references/boundaries-and-interfaces.md`.

## Background tasks

`lucid:dream` at `0 3 * * *` (3am local), `lucid:update` at `0 0 * * *`
(midnight daily). If the system was asleep at the 3am run, the morning gap
detector re-processes it: check the run-journal directory for the expected
`YYYY-MM-DD`, run `lucid.dream` once if absent, and log
`schedule_gap=missed→recovered`.

See `references/cron-execution.md` for cron-specific execution patterns and
`references/recovery-and-scheduling.md` for the job table.

## Ontology mapping

Lucid extracts no entities from user data; it classifies and routes journal
content produced by other skills. A Signal's `payload.type` reflects the entity
type found in the source journal (Person, Place, Concept, etc.) per
`spec-ocas-ontology.md`. Visibility: public.

## Scoring Traps

Misclassification traps that have caused real duplicate writes and noise
filings: ledger-before-re-filing, wall-clock run ids, payload-keys-are-not-
content, nested narrative extraction, MemPalace wing fallback, `re_evaluations`
null handling, and the buried-backlog targeted pass.

Read `references/scoring-traps.md` when a run files the wrong thing, files
something twice, or files nothing across several runs in a row.

## Support File Map

The full map — 16 references and 2 scripts, each with the condition under which
to read it — is in `references/support-file-map.md`. Read it when you are about
to run a cycle and need to know which detail file applies.

Most-reached:

| File | When to read |
|------|-------------|
| `references/classification.md` | Before classifying any journal entry. Scoring model, taxonomy, wing/room rules, skip criteria. |
| `references/dream-cycle.md` | Before executing the dream cycle. Phase-by-phase procedure, cursor tracking, filing pitfalls. |
| `references/gotchas.md` | Before any dream cycle run. Journal discovery, KG triples, null fields, log formats, cursor resumption. |

## Cron Execution Pattern

> **Critical**: `execute_code` is **blocked** in cron mode. Use `write_file` to
> write a Python script to `/tmp/`, then invoke it via
> `terminal(command="python3 /tmp/script.py")`.

The bundled `scripts/lucid_dream_template.py` implements the whole cycle — copy
it to `/tmp/` rather than writing one from scratch:

```bash
python3 /tmp/lucid_dream.py --help      # usage, no side effects
python3 /tmp/lucid_dream.py --dry-run   # classify + print, write nothing
python3 /tmp/lucid_dream.py --json      # machine-readable summary
```

Default batch is **200** journals per run — a 40-journal cap is consumed
entirely by scan files when the backlog is deep. Pass `--batch-size 40` for a
conservative pass.

Two rules that are not obvious from the code:

- **Sort by `(is_scan, skill_priority, filename)`, not alphabetically.**
  Alphabetical order puts scan/sweep journals first, so an early batch can be
  100% noise and file nothing.
- **Never block the cycle on MemPalace.** It is a write-side dependency;
  classification still has value when filing is unavailable, so degrade and
  queue rather than abort.

See `references/cron-execution-detail.md` for the priority table, skill-level
scan exceptions, the degraded-mode decision tree, and cron constraints.