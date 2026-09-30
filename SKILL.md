---
name: ocas-lucid
license: MIT
description: 'Canonical OCAS Dreaming implementation. Runs principal-scoped User Dreaming from Chronicle evidence and agent self-Dreaming from Autobio observations using one shared, domain-isolated kernel. User Dreaming writes accepted derivations through Chronicle; self-Dreaming stages evidence for Autobio/SOUL. The legacy journal curator remains available as lucid.curate only.'
source: https://github.com/<agent-handle>/lucid
includes:
- references/**
- scripts/**
triggers:
- lucid.user-dream
- lucid.self-dream
- lucid.curate
- lucid.status
- lucid.init
- lucid.update
metadata:
  author: Indigo Karasu (indigokarasu)
  version: "4.2.0"
  hermes:
    tags:
    - journaling
    - curation
    - memory
    - nightly-cron
    - ocas
    category: memory
---

# Lucid

Lucid is the canonical OCAS Dreaming implementation.

One repository owns the shared Dreaming machinery and two isolated domains:

- **User Dreaming**: Chronicle evidence → verified user-owned derivations →
  Chronicle durable memory.
- **Self Dreaming**: Autobio observation → self-domain staging/gating → evidence
  available to Autobio/SOUL.

Lucid owns neither canonical user memory nor canonical agent identity.
Chronicle remains the durable user-memory authority. Autobio/SOUL remains the
agent-identity authority.

The historical journal curator is retained as `lucid.curate` only. It is a
legacy compatibility path, not the primary Dreaming pipeline.

## Interactive Menu

When invoked interactively, present a two-level menu. See `references/interactive-menu.md` for the full menu structure.

## When to Use

- Nightly User Dreaming from Chronicle evidence.
- Daily self-Dreaming after Autobio observation.
- Manual `lucid.user-dream` / `lucid.self-dream` runs.
- Legacy `lucid.curate` only while curated-journal consumers remain.
- `lucid.status` to inspect per-principal run state.

## When NOT to Use

- Real-time memory filing during active sessions
- Skill evaluation or improvement proposals (Mentor)
- Agent behavioral adaptation (Praxis)
- Direct Chronicle storage/identity mutation outside sanctioned Chronicle contracts
- Inspecting a single known journal (just read the file)

## User Dreaming checklist

- [ ] Resolve exactly one target user principal (or require an explicit id).
- [ ] Read Chronicle descriptive interaction patterns since the last watermark.
- [ ] Re-open authoritative Chronicle evidence; reject cross-principal evidence.
- [ ] Stage a relationship-domain candidate.
- [ ] Apply the User Dreaming gate.
- [ ] Commit accepted derivations through Chronicle's atomic append/reducer path.
- [ ] Read the Chronicle event back and verify it.
- [ ] Promote Lucid relationship state only after durable verification.
- [ ] Record the run id, watermark, accepted/held/blocked counts, and write ids.

## Self Dreaming checklist

- [ ] Resolve the target agent principal.
- [ ] Read the latest Autobio observation.
- [ ] Stage only in the `self` namespace.
- [ ] Gate the observation as eligible/held/blocked.
- [ ] Record promoted self insight as Autobio-eligible evidence only.
- [ ] Never write SOUL or user memory.

## Legacy curator checklist

Run in order only for `lucid.curate` — each journal is processed to completion
(file + cursor advance) before the next, so a mid-run kill loses at most the
curator journal summary.

- [ ] **Orient** — load `config.json`; build the processed set from
      `ingestion_log.jsonl`; check for a >24h gap and run catch-up if needed
- [ ] **Gather** — discover unprocessed journals; sort by
      `(is_scan, skill_priority, filename)`; cap at `--batch-size` (default 200)
- [ ] **Classify** — extract narrative text (multi-path, not top-level only),
      score, assign taxonomy room; apply safety gates before filing
- [ ] **File** — check `decisions.jsonl` for an existing `file` decision on the
      source path first; if already filed, record `skip`/`already_filed` rather
      than writing a duplicate. **Normalize every logged path before comparing** —
      the `commons` symlink means the log and the filesystem spell the same
      journal differently, and a raw comparison returns False.
- [ ] **Close out** — append decisions + ingestion log + recirculation entries;
      write the dream journal; append evidence; advance `config.json` cursor,
      streak, and counters

## Initialization checklist

- [ ] Create `{agent_root}/commons/data/ocas-lucid/` and `staging/`
- [ ] Write default `config.json` with ConfigBase fields and skill-specific defaults
- [ ] Create empty `ingestion_log.jsonl`, `decisions.jsonl`,
      `recirculation_queue.jsonl`, `removed_entries.jsonl`
- [ ] Create `{agent_root}/commons/journals/ocas-lucid/`
- [ ] Run `python3 scripts/lucid_init.py --json`. It creates missing state,
      idempotently registers `lucid:user-dream` and `lucid:self-dream`, and
      migrates an existing `lucid:dream` job in place to `lucid:curate`.
- [ ] Use `--no-legacy-curator` when the deployment no longer has any consumer
      of curated-journal artifacts.
- [ ] Log initialization as a DecisionRecord

## Error handling

| Failure | Symptom | Handling |
|---------|---------|----------|
| `config.json` missing | Script exits `2` before processing | Run `lucid.init`, then re-run. Do not hand-write a config — the cursor format is load-bearing for resumption. |
| Source journal is malformed JSON | `read_error` recorded, score `-3`, run continues | Producer-side bug (commonly `ocas-mentor`). Do not patch the journal in place — the cursor will re-read it and the fix will be overwritten. |
| Curated journal write fails | `curated_write_failed`; source journal remains evidence | Do not fabricate success; retry that source on the next repair pass. |
| Chronicle ingestion unavailable | Curated journal still exists with optional candidate | Non-fatal to Lucid. Chronicle ingestion is downstream and independently recoverable. |
| Backlog > 1000 journals, batch files nothing | `file_count: 0` across several runs | Cursor is buried in scan-heavy territory. Run a targeted pass over high-signal skills only (vesper, praxis, taste, custodian, dispatch). |
| `update.sh` exits 3 | "worktree has uncommitted changes" | **Refusal, not a failure.** Commit or stash, or pass `--force` to discard deliberately. |

Full table — including duplicate-filing, wing-fallback, and divergence cases —
in `references/error-handling.md`.

## Responsibility boundary

Lucid owns Dreaming orchestration, principal/domain isolation, candidate state,
gating, run/watermark state, and the User/Self Dreaming execution paths.

Lucid does **not** own Chronicle evidence or canonical durable user memory;
Chronicle does. Lucid does **not** own Indigo identity; Autobio/SOUL does.
Lucid does **not** own system-improvement behavior; Finch/Praxis/Mentor/Forge
do. The legacy curator owns only its compatibility journal artifacts.

Read `references/boundaries-and-interfaces.md` when deciding which component should handle a task or when wiring a new consumer of Lucid output.

## Commands

- `lucid.user-dream` — User Dreaming now.
- `lucid.self-dream` — self-Dreaming now.
- `lucid.curate` — legacy journal curation compatibility cycle.
- `lucid.status` — Dreaming + legacy curator status.
- `lucid.init` — initialize state and register subject-specific jobs.
- `lucid.update` — update Lucid while preserving state.

### Bundled scripts

| Script | Usage | Exit codes |
|--------|-------|-----------|
| `scripts/lucid_user_dream.py` | `--principal`, `--since-seq`, `--limit`, `--json` | 0 clean run, 1 durable-write error |
| `scripts/lucid_self_dream.py` | `--principal`, `--observation`, `--observations-dir`, `--json` | 0 completed/no-op |
| `scripts/lucid_init.py` | initialize state + reconcile/migrate Lucid cron jobs | 0 reconciled, 1 mismatch/failure |
| `scripts/lucid_status.py` | report Lucid cron and principal/domain run state | 0 completed |
| `scripts/lucid_curate.py` | compatibility wrapper for the old journal cycle | follows legacy curator |
| `scripts/lucid_dream_template.py` | legacy implementation behind `lucid.curate` | 0 completed/help, 2 bad usage or missing config |
| `scripts/update.sh` | `--help`, `--dry-run`, `--force` | 0 updated, 2 bad usage, 3 dirty worktree (refused), 4 divergence/pull failure |

Both scripts are safe to invoke with `--help`: they print usage and exit 0
without touching journal, log, or config state. Use `--dry-run` on the dream
cycle to preview a batch before it advances the cursor.

## Recovery behavior

Implements the recovery contract from `spec-ocas-recovery.md`: an evidence
record on every cycle (including skip/hibernation runs), >24h gap detection
with a capped catch-up pass, retryable curated-artifact failures, and
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
`journal_spec_version "2.0"`, `type: "Observation"`. Carries the same counters plus `file_details`,
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
genuine change, and a lost or falsely acknowledged curated artifact is the expensive failure.
Hibernation exists so a quiet night produces an explicit "no activity" record
rather than an empty journal that later reads as a failed run.

## Dream journal output

Journal type: Observation. Written to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json` using JournalEntry v2 semantics and explicit principal metadata when a candidate is eligible.

See `references/dream-journal.md` for the full journal schema (scan/file/skip counts, re-emergence events, Signal payload, skip path).

## OKR evaluation

Universal OKRs per `spec-ocas-journal.md`, plus skill-specific targets. See `references/okr.md` for the full OKR table (ingestion coverage, duplicate avoidance, recirculation, Signal precision, schedule adherence, data integrity).

## Inter-skill interfaces

Reads all skill journals from `{agent_root}/commons/journals/` (read-only);
writes only its own curated journals, candidate payloads, and private data files. Durable memory ingestion belongs to Chronicle sanctioned contracts. Full read/write/query surface in
`references/boundaries-and-interfaces.md`.

## Background tasks

Required:

- `lucid:user-dream` — daily 02:20 local.
- `lucid:self-dream` — daily 00:05 local, after the late-evening Autobio
  observation window. Re-running the same observation is a recorded no-op.

Optional during migration:

- `lucid:curate` — legacy curator only while a downstream consumer remains.

See `references/dreaming-scheduling.md` for the canonical schedules.

## Ontology mapping

Lucid extracts no entities from user data; it classifies and routes journal
content produced by other skills. A Signal's `payload.type` reflects the entity
type found in the source journal (Person, Place, Concept, etc.) per
`spec-ocas-ontology.md`. Visibility: public.

## Scoring Traps

Misclassification traps that have caused real duplicate writes and noise
filings: ledger-before-re-filing, wall-clock run ids, payload-keys-are-not-
content, nested narrative extraction, principal eligibility, `re_evaluations`
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
- **Never infer a user-memory owner.** Classification remains useful even when a source journal has no explicit principal. Curate the evidence, set `memory_candidate: null`, and let downstream principal-aware systems decide whether it is eligible for durable memory.

See `references/cron-execution-detail.md` for the priority table, skill-level
scan exceptions, the degraded-mode decision tree, and cron constraints.