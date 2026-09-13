# Operational Pitfalls & Gotchas

## Payload Keys vs Narrative Content (CRITICAL)

**The `correction_or_lesson(+4)` signal must ONLY fire on narrative text fields.**

DO NOT count payload dictionary key names like:
- `lessons_extracted` — this is a key name, not a lesson
- `events_recorded` — metric, not narrative
- `signals_created` — metric, not narrative
- `ingest complete: 7 journals scanned, 1 new events, 9 new lessons` — "lessons" here is a COUNT, not narrative content

**Narrative fields only**: `decision.summary`, `decision.description`, `decision.reasoning_summary`, `action.side_effect_intent`, `action.reason`, `urgent_issues[].summary`, `anomalies[].summary`

---

## Timestamp Parsing Edge Cases

| Format | Example | Parser Behavior |
|--------|---------|-----------------|
| Standard | `mentor-light-20260726T104224Z.json` | Extract `20260726T104224Z` suffix |
| ISO with colons | `mentor-2026-07-27T13:59:01Z.json` | Normalize: strip non-alphanumeric except T/Z, compare lexicographically |
| Date-only directory | `2026-07-27/` | Filename suffix takes precedence over directory date |
| Malformed | `mentor-light.json` | Skip (no timestamp) — log warning |

Lexicographic comparison works because `YYYYMMDDTHHMMSSZ` is fixed-width zero-padded.

---

## MemPalace Wing Fallback

`mempalace_list_wings` may return ONLY `root` (no custom wings created yet).

**Correct behavior**: File into `root/<wing_topic_slug>` using the wing's topic slug as the room name.

**Wrong**: Attempt to create custom wings via MCP (not supported). Do not skip filing because wing doesn't exist.

---

## KG Write Mandate

**If classification identified KG triples, you MUST call `mempalace_kg_add` for each.**

Filing only the drawer and silently skipping KG loses relationship data permanently. There is no deferred KG write.

---

## Reference File Resilience

Reference files in Support File Map may not exist on disk (e.g., `platform-notes.md`, `okr.md`).

**Rule**: Fall back to SKILL.md body content. Do not block the run. Log missing reference in dream journal signals.

---

## Recirculation Queue Staleness

Entries in `recirculation_queue.jsonl` older than `reemergence_max_queue_size` (default 200) should be moved to `removed_entries.jsonl` with reason `queue_overflow` — do not let the queue grow unbounded.

---

## Cursor Filename Comparison

The cursor is a **journal filename**, not a timestamp. Example: `mentor-light-20260726T104224Z.json`.

To find unprocessed journals:
1. Extract `YYYYMMDDTHHMMSSZ` suffix from each journal filename
2. Extract same suffix from cursor filename
3. Compare lexicographically (string comparison works for zero-padded ISO-like format)
4. Also parse ISO-format timestamps with colons for journals using that pattern

---

## MemPalace MCP Tool Invocation

MemPalace tools are Python functions from `mempalace.mcp_server`, NOT registered MCP tools.

```python
from mempalace.mcp_server import (
    tool_status,
    tool_check_duplicate,
    tool_add_drawer,
    tool_kg_add,
    tool_search
)
```

These functions use internal globals initialized from `MempalaceConfig()` which defaults to `~/.mempalace/palace`. Ensure the palace directory exists before calling tools.

---

## Degraded Mode Cursor Behavior

In degraded mode (MemPalace unavailable):
- Cursor does NOT advance
- Next run will re-process same journals (idempotent via duplicate check)
- This is correct behavior — ensures no journals are lost

---

## Catchup Cap Interaction

`catchup_cap` (default 40) limits journals processed per run. If more than cap are pending:
- Oldest `catchup_cap` journals processed
- Cursor advances to last processed
- Remaining journals processed on subsequent runs
- This prevents timeout/memory issues on large backlogs