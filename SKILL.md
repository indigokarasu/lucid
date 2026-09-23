---
name: ocas-lucid
description: 'Nightly journal curator. Batch-processes OCAS skill journals via relevance classification and writes curated content to journal files for the configured memory provider to ingest. Use when running scheduled nightly curation at 3am, manually invoking lucid.dream, or checking lucid.status. NOT for real-time memory filing, skill evaluation, behavioral detection, or entity resolution.'
license: MIT
source: https://github.com/indigokarasu/lucid
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 3.0.1
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
- Hibernation: if no new journals for `hibernation_days` (default 7), skip with zero IO

### Gather
- Scan `~/.hermes/commons/journals/` for skill journal `.json` files
- Exclude Lucid's own directory (config: `exclude_self: true`)
- Keep journals whose filename timestamp is greater than the cursor
- Cap at `catchup_cap` (default 40)

### Classify
Extract text from narrative fields only — never from payload dict keys. A key
named `lessons_extracted` is not a lesson.

Apply scoring signals additively:

| Signal | Score |
|---|---|
| Decision keywords (`decided`, `confirmed`, `agreed`, `resolved`, `committed`, `approved`, `rejected`) | +3 |
| Entity density (3+ named entities in narrative text) | +2 |
| Correction or lesson (narrative fields only) | +4 |
| User-directed action | +3 |
| Emotional signal | +2 |
| Cross-skill reference | +2 |
| Relationship signal (person ↔ person/project/org) | +3 |
| Pure metrics | −3 |
| Routine health check (ocas-custodian) | −4 |

Thresholds: **≥5** write, **3–4** skip and recirculate, **≤2** skip.

### Write
- Write the curated entries into `~/.hermes/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`
- Append a DecisionRecord per journal to `decisions.jsonl`
- Update `ingestion_log.jsonl` and advance the cursor

The memory provider picks these up on its own schedule. Lucid's job ends when
the journal is written.

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

- `references/self-update-lucid.md` — Self-Update Procedure for Lucid
