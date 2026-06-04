---
name: ocas-lucid
description: 'Nightly journal curator. Batch-processes OCAS skill journals into MemPalace''s
  verbatim store via MCP tools. Classifies each journal for filing as a MemPalace
  drawer, MemPalace KG triple, Elephas Signal, or skip. Features re-emergence detection,
  two-pass stale handling, change magnitude gates, hibernation protection, and incremental
  cursor-based resumption. Trigger: dream cycle, journal consolidation, MemPalace
  filing, memory curation, "run lucid", "what did I dream", "journal curation", nightly
  batch. NOT for real-time memory filing, skill evaluation, behavioral pattern detection,
  or entity identity resolution.

  '
license: MIT
source: https://github.com/indigokarasu/lucid
includes:
- references/**
- scripts/**
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 2.0.4
triggers:
- nightly journal
- journal curation
- skill journal batch
- mem-Palace filing
- curate journals
---

# Lucid

Nightly journal curator. Batch-processes journals from all OCAS skills into MemPalace's verbatim semantic store. Structured facts worth promoting to Chronicle are emitted as Signals to Elephas via the journal signal payload -- Lucid never writes to Chronicle or Weave directly.

## Interactive Menu

When invoked interactively (via `/` command), present a menu using the `clarify` tool so the user can pick which function to run.

```python
result = clarify(
    question="What would you like to do?",
    choices=[
        "dream — Run the full dream cycle",
        "status — Show system status",
        "init — Initialize environment",
        "update — Pull latest from GitHub",
    ]
)
```

After the user selects an action, execute it following the relevant procedure in this skill. Loop back to the menu after each action completes, until the user chooses to exit or sends `/stop`.

### Response parsing

Match the user's response against the full choice string. If the response doesn't match any known choice (user typed free-form via "Other"), match key prefixes case-insensitively. Re-present the menu on no match.

### Platform adaptation

On CLI, choices are navigable with arrow keys. On messaging platforms, choices render as a numbered list.


## When to Use

- Scheduled nightly cron at 3am (primary mode)
- Manual invocation via `lucid.dream` for immediate processing
- `lucid.status` to check last run, pending journals, filing stats

## When NOT to Use

- Real-time memory filing during active sessions
- Skill evaluation or improvement proposals (Mentor)
- Behavioral pattern detection (Corvus)
- Entity identity resolution (Elephas)

## Responsibility boundary

Lucid owns: nightly journal scanning, MemPalace filing (drawers + KG), relevance classification, weak signal recirculation, re-emergence detection.

Lucid does not own: Chronicle writes (Elephas only), social graph updates (Weave only), real-time pattern analysis (Corvus), skill performance evaluation (Mentor).

Adjacent boundaries: Elephas also reads journals but for structured entity extraction and Chronicle promotion. Mentor also reads journals but for OKR evaluation. Lucid reads journals for verbatim preservation and semantic searchability via MemPalace.

## Optional skill cooperation

- **Elephas**: Lucid queries Chronicle via `elephas.query` to check if an entity already exists before emitting a Signal. If Elephas is unavailable, Lucid emits the Signal anyway (Elephas deduplicates on ingestion).
- **MemPalace**: Required. Lucid uses MemPalace MCP tools for all filing operations. If MemPalace is unavailable, Lucid logs failures and skips filing for that run.

## Commands

- `lucid.dream` -- run the full dream cycle immediately, ignoring the time gate
- `lucid.status` -- last run timestamp, journals pending, cumulative filing stats, streak count
- `lucid.init` -- create storage directories, initialize config and logs, register cron jobs
- `lucid.update` -- pull latest from GitHub source; preserves journals and data

## Recovery Behavior

This skill implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence**: Every dream cycle writes an evidence record to `{agent_root}/commons/data/ocas-lucid/evidence.jsonl`, including skip/hibernation runs. The `not_activity_reason` field is mandatory when no side effects occur.
- **Gap detection**: On every wake, checks the evidence log. If gap exceeds 24h for dream cycle, logs `gap_detected` and runs a catch-up pass (capped at 40 journals).
- **Degraded mode**: When MemPalace MCP is unavailable, logs `degraded: mempalace` and queues filing for retry. When journal sources are missing, continues with available sources.
- **Log compaction**: Ingestion logs older than 30 days (no-op) or 90 days (error/gap) compacted. Last 7 days retained.

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

## Initialization

On `lucid.init` or first invocation:

1. Create `{agent_root}/commons/data/ocas-lucid/` and subdirectories (`staging/`)
2. Write default `config.json` with ConfigBase fields and skill-specific defaults
3. Create empty `ingestion_log.jsonl`, `decisions.jsonl`, `recirculation_queue.jsonl`, `removed_entries.jsonl`
4. Create `{agent_root}/commons/journals/ocas-lucid/`
5. Register cron jobs `lucid:dream` and `lucid:update` if not already present (check before registering)
6. Log initialization as a DecisionRecord

## Dream cycle

Four phases executed sequentially. Each journal is processed to completion (file + cursor advance) before moving to the next, ensuring mid-run termination loses no filed work.

See `references/dream-cycle.md` for the full phase-by-phase procedure (Orient, Gather, Classify, File), cursor tracking, and filing pitfalls.

### Incremental cursor

The ingestion log tracks each processed run_id. If the session terminates mid-run, the next cycle resumes from the first unprocessed journal. Filed content and cursor updates are durable — only the dream journal summary is lost on interruption.

## Re-emergence detection & stale handling

See `references/re-emergence.md` for the full re-emergence algorithm (3+ journal threshold, auto-promotion) and two-pass stale handling (mark on first contradiction, invalidate on second confirmation).

## Safety gates

See `references/safety-gates.md` for change magnitude gates (>30% warning, >50% staging hold) and hibernation protection (7-day no-new-journals → skip with zero IO).

## Dream journal output

Journal type: Action (writes to MemPalace are external side effects). Written to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json` using the standard JournalEntry schema with `journal_spec_version "1.3"`.

See `references/dream-journal.md` for the full journal schema (scan/file/skip counts, re-emergence events, Signal payload, skip path).

## OKR evaluation

Universal OKRs per `spec-ocas-journal.md`, plus skill-specific targets. See `references/okr.md` for the full OKR table (ingestion coverage, duplicate avoidance, recirculation, Signal precision, schedule adherence, data integrity).

## Inter-skill interfaces

**Reads (all read-only):**
- All skill journals from `{agent_root}/commons/journals/` (same access pattern as Mentor and Elephas)

**Writes:**
- MemPalace drawers and KG via MCP tools (external)
- Signal payload field in own dream journal (standard Signal schema from spec-ocas-shared-schemas.md)
- Own journal, data, and decisions files only

**Queries:**
- `mempalace_status`, `mempalace_search`, `mempalace_check_duplicate`, `mempalace_get_taxonomy` (read)
- `mempalace_add_drawer`, `mempalace_kg_add`, `mempalace_kg_invalidate` (write)
- `elephas.query` (optional, for pre-emission entity existence check)

## Background Tasks

| Job name | Mechanism | Schedule | Command |
|----------|-----------|----------|---------|
| `lucid:dream` | cron | `0 3 * * *` (3am local) | `lucid.dream` |
| `lucid:update` | cron | `0 0 * * *` (midnight daily) | `lucid.update` |

See `references/platform-notes.md` for iteration budget, timeout behavior, and mid-run termination safety.

## Ontology mapping

Lucid extracts no entities from user data directly. It classifies and routes journal content produced by other skills. When it emits Signals to Elephas, the Signal's `payload.type` reflects the entity type found in the source journal (Person, Place, Concept, etc.) per spec-ocas-ontology.md.

## Self-Update

See `references/self-update-lucid.md`.

## Visibility

public

## Gotchas

See `references/gotchas.md` for all operational pitfalls including journal discovery, KG triple sanitization, null field handling, ingestion log format variance, cursor resumption, and recirculation queue edge cases.

### Scoring trap: payload keys vs. narrative content

The `correction_or_lesson(+4)` signal must ONLY fire on narrative text fields (`summary`, `description`, `reasoning_summary`). Do NOT count payload dictionary **key names** (like `lessons_extracted`) as content — this causes routine operational journals to score 6+ and get filed as noise. Apply keyword checks to the extracted narrative text only, not to the full serialized JSON.

### MemPalace wing fallback

`mempalace_list_wings` may return only `root` even though the classification taxonomy defines wings like `wing_research`, `wing_knowledge`, etc. When this happens, file into `root/<room>` where `<room>` is the wing's topic slug (e.g., `root/preferences`, `root/operations`, `root/evolution`). Do not attempt to create custom wings via MCP — it is not supported.

### Always execute KG writes

During Phase 4 (File), if the classification phase identified KG triples for a journal, you MUST call `mempalace_kg_add` for each triple. Filing only the drawer and silently skipping KG writes loses relationship data. The classification step identifies triples; the filing step must persist them.

### Reference file resilience

`references/dream-cycle.md`, `references/re-emergence.md`, `references/safety-gates.md`, and `references/dream-journal.md` may not exist on disk even though the Support File Map references them. When a reference file is missing, fall back to the procedural instructions in the SKILL.md body itself. Do not block the run.

## Support File Map

| File | When to read |
|------|-------------|
| `references/classification.md` | Before classifying any journal entry. Contains the relevance scoring model, filing taxonomy, wing/room assignment rules, and skip criteria. |
| `references/dream-cycle.md` | Before executing the dream cycle. Phase-by-phase procedure (Orient, Gather, Classify, File), cursor tracking, and filing pitfalls. |
| `references/re-emergence.md` | During post-file cleanup. Re-emergence detection (3+ threshold, auto-promotion) and two-pass stale handling. |
| `references/safety-gates.md` | After classification, before filing. Change magnitude gates (>30% warning, >50% staging hold) and hibernation protection. |
| `references/dream-journal.md` | When writing the dream journal. Full output schema (counts, events, Signal payload, skip path). |
| `references/okr.md` | During OKR evaluation. Skill-specific targets for ingestion coverage, duplicate avoidance, recirculation, Signal precision, schedule adherence, data integrity. |
| `references/gotchas.md` | Before any dream cycle run. Operational pitfalls for journal discovery, KG triples, null fields, ingestion log formats, cursor resumption, and recirculation queue. |
