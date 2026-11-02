---
name: ocas-lucid
description: 'Curates OCAS skill journals nightly. Classifies journal entries by relevance and writes curated content to journal files for the memory provider to ingest. Triggers on nightly journal curation, skill journal batch processing, and lucid.dream invocation. NOT for real-time memory filing, skill evaluation, behavioral detection, or entity resolution.'
license: MIT
source: https://github.com/indigokarasu/lucid
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 3.0.2
  hermes:
    tags: [journal, curation, nightly, OCAS-core]
    category: creative
includes:
  - references/**
  - scripts/**
tags:
- journal
- curation
- nightly
- OCAS-core
triggers:
- nightly journal
- journal curation
- skill journal batch
- curate journals
---


# Lucid

Nightly journal curator. Batch-processes journals from all OCAS skills, scores
them for relevance, and writes the ones worth keeping into Lucid's own journal
files. The configured memory provider reads those journals on its own ingestion
cycle and decides what to persist.

Lucid does not write to a memory store directly. It curates; the provider
ingests. That boundary is the whole point of the skill — it keeps scoring
auditable and keeps Lucid unaware of whatever store is configured.

## When to Use
- Scheduled nightly cron (primary mode)
- Manual invocation via `lucid.dream` for immediate processing
- `lucid.status` to check last run, pending journals, filing stats, streak count

## When NOT to Use
- Real-time memory filing during active sessions
- Skill evaluation or improvement proposals (Mentor)
- Behavioral pattern detection (Corvus)

## Pipeline: Orient → Gather → Classify → Write

- [ ] **Orient:** read config → check cursor → check hibernation
- [ ] **Gather:** scan journals → exclude self → filter by cursor → cap at 40
- [ ] **Classify:** extract narrative text → apply scoring signals → decide
- [ ] **Write:** record decisions → write the curated journal

Classify must precede Write because the score decides what gets written. Write
is last because it is the only step with side effects.

### Orient
- Read `~/.hermes/commons/data/ocas-lucid/config.json`
- Check the cursor — the last-processed journal filename
- Hibernation: if no new journals for `hibernation_days` (default 7), skip with zero IO — 7 days avoids wasting cycles on a quiet system while still catching up within a week of inactivity

### Gather
- Scan `~/.hermes/commons/journals/` for skill journal `.json` files
- Exclude Lucid's own directory (config: `exclude_self: true`) — prevents recursive self-curation and infinite loops
- Keep journals whose filename timestamp is greater than the cursor
- Cap at `catchup_cap` (default 40) — limits a single run to a manageable batch so one slow cycle doesn't block the agent

### Classify
Extract text from narrative fields only — never from payload dict keys. A key
named `lessons_extracted` is not a lesson.

Apply scoring signals additively. Each weight reflects how strongly the signal
indicates information worth persisting across sessions — corrections and decisions
outrank observations because they change future behavior, while routine metrics
and health checks are actively penalized to prevent noise accumulation.

| Signal | Score | Why |
|---|---|---|
| Decision keywords (`decided`, `confirmed`, `agreed`, `resolved`, `committed`, `approved`, `rejected`) | +3 | Decisions are commitments that constrain future choices; losing them causes repeated deliberation |
| Entity density (3+ named entities in narrative text) | +2 | Dense entity references indicate a substantive interaction, not a trivial exchange |
| Correction or lesson (narrative fields only) | +4 | Corrections are the highest-value signal — they prevent repeated mistakes and directly improve future behavior |
| User-directed action | +3 | Actions the user explicitly requested are outcomes they expect to be remembered |
| Emotional signal | +2 | Emotional weight correlates with importance and aids later retrieval |
| Cross-skill reference | +2 | Links between skills indicate shared context that benefits from unified memory |
| Relationship signal (person ↔ person/project/org) | +3 | Relationship changes are durable facts with high reuse value |
| Pure metrics | −3 | Raw numbers without narrative context are replaceable by re-querying the source |
| Routine health check (ocas-custodian) | −4 | Health checks are repetitive and low-information; penalizing them prevents journal bloat |

Thresholds: **≥5** write, **3–4** skip and recirculate, **≤2** skip.
- **≥5 write**: A single strong signal (correction +4 plus any +1) or two medium signals clears the bar — only entries with genuine informational value are written.
- **3–4 skip and recirculate**: Borderline entries are not discarded; they re-enter the next cycle where additional context may push them over the threshold.
- **≤2 skip**: Entries below this have no actionable content; writing them wastes storage and dilutes retrieval quality.

### Write
- Write the curated entries into `~/.hermes/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`
- Append a DecisionRecord per journal to `decisions.jsonl`
- Update `ingestion_log.jsonl` and advance the cursor

The memory provider picks these up on its own schedule. Lucid's job ends when
the journal is written.

### Input / Output Examples

**Input:** journal files in `~/.hermes/commons/journals/` named `<skill>/<YYYYMMDDTHHMMSSZ>.json`, each containing narrative text fields and a cursor file at `~/.hermes/commons/data/ocas-lucid/config.json` recording the last-processed filename.

**Output:** curated entries written to `~/.hermes/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`, with a `DecisionRecord` appended to `decisions.jsonl` and the cursor advanced in `ingestion_log.jsonl`.

## Gotchas

### Payload keys are not narrative
The correction/lesson signal (+4) must fire only on narrative text. Counting
payload dictionary key names inflates every journal that has a `lessons_*` key.

### Chronological ordering comes from the filename
Extract the `YYYYMMDDTHHMMSSZ` suffix from the journal filename, not from the
directory date, and compare lexicographically against the cursor. Some journals
use ISO timestamps with colons — parse those too.

### Reference files may be absent
Fall back to this file's body. Do not block a run on a missing reference.

### Never fabricate a write
If a step cannot complete, record the degradation and skip — do not log a
filing that did not happen. See `infrastructure/degraded-mode-execution`.

## Error Handling

| Failure | Handling |
|---------|----------|
| Journal JSON corrupt | Log filename; skip that file; continue |
| Cursor file missing | Start from the earliest journal; cursor resets on next success |
| Score ties (3–4) | Skip and recirculate; do not write borderline entries |
| No new journals | Hibernate per `hibernation_days`; zero IO |

## Storage layout
```
~/.hermes/commons/data/ocas-lucid/
  config.json, ingestion_log.jsonl, decisions.jsonl,
  recirculation_queue.jsonl, removed_entries.jsonl, staging/, evidence.jsonl

~/.hermes/commons/journals/ocas-lucid/
  YYYY-MM-DD/{run_id}.json
```

## Support Files

| File | Purpose | When to read |
|------|---------|--------------|
| `references/self-update-lucid.md` | Self-Update Procedure for Lucid | Before updating the skill repository or reloading configuration |
| `CHANGELOG.md` | Version history and release notes | When checking what changed between versions or verifying a fix was shipped |
| `config.json` | Runtime configuration (cursor, hibernation, thresholds) | When debugging cursor state or adjusting hibernation/catchup parameters |
| `data/activity_model.jsonl` | Historical activity model data | When analyzing filing patterns or tuning scoring weights |
| `infrastructure/degraded-mode-execution` (external skill) | Degraded-mode execution protocol | When a pipeline step cannot complete and the run must degrade gracefully |
