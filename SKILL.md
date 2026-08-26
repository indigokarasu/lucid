---
name: ocas-lucid
description: Nightly journal curator. Batch-processes OCAS skill journals via relevance classification and writes curated content to journal files for the configured memory provider to ingest.
license: MIT
source: https://github.com/indigokarasu/lucid
metadata:
  author: Indigo Karasu (indigokarasu)
  version: 3.0.1
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

Nightly journal curator. Batch-processes journals from all OCAS skills, classifies them by relevance, and writes curated content to Lucid's own journal files. The configured memory provider reads these journals during its ingestion cycle and decides what to persist.

## When to Use
- Scheduled nightly cron at 3am (primary mode)
- Manual invocation via `lucid.dream` for immediate processing
- `lucid.status` to check last run, pending journals, filing stats, streak count

## When NOT to Use
- Real-time memory filing during active sessions
- Skill evaluation or improvement proposals (Mentor)
- Behavioral pattern detection (Corvus)
- Entity identity resolution (Elephas)

## Responsibility boundary
Lucid owns: nightly journal scanning, MemPalace filing (drawers + KG), relevance classification, weak signal recirculation, re-emergence detection.
Lucid does not own: Chronicle writes (Elephas only), social graph updates (Weave only), real-time pattern analysis (Corvus), skill performance evaluation (Mentor).

## Dream cycle (Orient → Gather → Classify → File)

### Phase 1 (Orient)
- Read `~/.hermes/commons/data/ocas-lucid/config.json`
- Check cursor — the last-processed journal filename
- Call `mempalace_status` to verify MemPalace availability
- Check hibernation: if no new journals for `hibernation_days` (default 7), skip with zero IO

### Phase 2 (Gather)
- Scan `~/.hermes/commons/journals/` for all skill journal `.json` files
- Exclude `ocas-lucid` own directory (config: `exclude_self: true`)
- Filter to journals with filename timestamp > cursor timestamp (lexicographic comparison on the `YYYYMMDDTHHMMSSZ` segment)
- Cap at `catchup_cap` (default 40)

### Phase 3 (Classify)
- For each journal, extract text from narrative fields only (NOT payload dict keys)
- Apply scoring signals additively:
  - Decision keywords (`decided`, `confirmed`, `agreed`, `resolved`, `committed`, `approved`, `rejected`): +3
  - Entity density (3+ named entities in narrative text): +2
  - Novel entities (not in MemPalace — check via `mempalace_search`): +3
  - Correction/lesson (only in narrative fields, not keys): +4
  - User-directed action: +3
  - Emotional signal: +2
  - Cross-skill reference: +2
  - Relationship signal (person ↔ person/project/org): +3
- Penalties: Pure metrics -3, Routine health check (ocas-custodian) -4, Duplicate (mempalace_check_duplicate >0.9) -5
- Thresholds: >=5 file, 3-4 skip+recirculate, <=2 skip
- Wing assignment by source skill domain (see classification reference)

### Phase 4 (File)
- For each filing decision, call actual MemPalace MCP tools:
  - `mempalace_check_duplicate` before filing any drawer
  - `mempalace_add_drawer` for drawer filings (wing, room, content, source_file)
  - `mempalace_kg_add` for KG triples (subject, predicate, object, valid_from)
- Append DecisionRecord to `decisions.jsonl`
- Update `ingestion_log.jsonl`
- Write dream journal to `~/.hermes/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`

## Scoring Traps

### Payload keys vs. narrative content
The `correction_or_lesson(+4)` signal must ONLY fire on narrative text fields. Do NOT count payload dictionary key names (like `lessons_extracted`) — keyword checks apply to extracted narrative text only.

### MemPalace wing fallback
`mempalace_list_wings` may return only `root`. File into `root/<room>` using the wing's topic slug. Do not create custom wings via MCP.

### Always execute KG writes
If classification identified KG triples, you MUST call `mempalace_kg_add` for each. Filing only the drawer and silently skipping KG loses relationship data.

### Reference file resilience
Reference files may not exist on disk even though Support File Map references them. Fall back to SKILL.md body. Do not block the run.

### Chronological ordering of journal files
Extract the timestamp from the filename suffix `YYYYMMDDTHHMMSSZ`, not from directory date alone. Compare lexicographically against cursor filename. Files with non-standard formats (ISO dates with colons) should also be parsed and compared.

### Incremental cursor via filename comparison
The cursor is a journal filename (e.g., `mentor-light-20260726T104224Z.json`). To find unprocessed journals, extract the `YYYYMMDDTHHMMSSZ` suffix from each journal filename and compare lexicographically. Any journal with a filename suffix greater than the cursor's is unprocessed. Also parse ISO-format timestamps with colons (e.g., `2026-07-27T13:59:01Z`) for journals that use that pattern.

### MemPalace MCP tool invocation
MemPalace tools are Python functions from `mempalace.mcp_server`, not registered MCP tools. Import and call them directly:
- `from mempalace.mcp_server import tool_status, tool_check_duplicate, tool_add_drawer, tool_kg_add, tool_search`
- `tool_status()` — no args, returns drawer count and wing/room breakdown
- `tool_check_duplicate(content, threshold=0.9)` — content string, returns is_duplicate + matches
- `tool_add_drawer(wing, room, content, source_file=None, added_by='mcp')` — files verbatim content
- `tool_kg_add(subject, predicate, object, valid_from=None, source_closet=None)` — adds KG triple
- `tool_search(query, limit=5, wing=None, room=None)` — semantic search

These functions use internal globals initialized from `MempalaceConfig()` which defaults to `~/.mempalace/palace`. Ensure the palace exists before calling tools.

## Storage layout
```
~/.hermes/commons/data/ocas-lucid/
  config.json, ingestion_log.jsonl, decisions.jsonl, recirculation_queue.jsonl, removed_entries.jsonl, staging/, evidence.jsonl, pending_mempalace.jsonl

~/.hermes/commons/journals/ocas-lucid/
  YYYY-MM-DD/{run_id}.json
```

## Support File Map
| File | When to read |
|------|-------------|
| `references/classification.md` | Before classifying any journal entry — scoring model, filing taxonomy, wing/room rules |
| `references/dream-cycle.md` | Before executing the dream cycle — phase-by-phase procedure |
| `references/dream-journal.md` | When writing the dream journal — output schema |
| `references/re-emergence.md` | During post-file cleanup — re-emergence detection, two-pass stale handling |
| `references/safety-gates.md` | After classification, before filing — change magnitude gates, hibernation protection |
| `references/gotchas.md` | Before any dream cycle run — operational pitfalls |
| `references/okr.md` | During OKR evaluation |
| `references/platform-notes.md` | Platform-specific execution notes |
| `references/self-update-lucid.md` | Self-update procedure |