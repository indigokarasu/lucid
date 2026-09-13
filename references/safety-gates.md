# Safety Gates & Hibernation Protection

## Change Magnitude Gates

Before any filing operation, verify the change magnitude is within safe bounds:

| Gate | Check | Failure Action |
|------|-------|----------------|
| **Drawer count delta** | `mempalace_status()` before/after — drawer increase ≤ `max_drawers_per_run` (default 20) | Abort filing, alert via decisions.jsonl, keep cursor unchanged |
| **KG triple delta** | Triple increase ≤ `max_kg_per_run` (default 30) | Abort filing, alert |
| **Recirculation queue growth** | Queue size ≤ `max_queue_size` (default 200) | Pause re-emergence pass, log warning |
| **Cursor advancement** | Cursor only advances after successful Phase 4 commit | Rollback cursor on any Phase 4 failure |

## Hibernation Protection

If no new journals for `hibernation_days` (default 7):
- Skip entire dream cycle (zero IO)
- Write dream journal entry: `mode: "hibernation"`, `skip_path: "no new journals for N days"`
- Do NOT update cursor
- Do NOT process recirculation queue

**Exception**: Manual invocation via `lucid.dream` bypasses hibernation check.

## Degraded Mode (MemPalace Unavailable)

If `mempalace_status()` returns unavailable or tools raise connection errors:
- Set `mode: "degraded: mempalace"` in dream journal
- Queue all filing decisions to `pending_mempalace.jsonl` with full context
- Continue scanning/classifying (no IO to palace)
- Write dream journal with `mempalace_available: false`, `pending_mempalace: N`
- On next run, if palace recovers: drain `pending_mempalace.jsonl` first (FIFO), then normal cycle

## Duplicate Protection

**Mandatory**: Call `mempalace_check_duplicate(content, threshold=0.9)` before EVERY `mempalace_add_drawer`.
- If duplicate: skip filing, increment skip_count, log to decisions.jsonl with `duplicate: true`
- Do NOT call `mempalace_kg_add` for duplicate content

## Cursor Integrity

- Cursor only updates AFTER successful Phase 4 (all filings committed, logs written, dream journal written)
- Cursor value = last successfully processed journal filename
- If Phase 4 partially fails: cursor unchanged, full re-run on next cycle (idempotent via duplicate check)
- Cursor stored in config.json with timestamp of last successful run

## Why These Gates Are Rigid

- **Drawer/KG delta limits**: MemPalace is a semantic memory; uncontrolled growth degrades retrieval quality and correlates with palace corruption in stress tests
- **Hibernation**: Prevents spinning on empty directories; palace writes have fixed overhead
- **Degraded mode queue**: Guarantees no data loss during palace downtime; FIFO drain preserves temporal order
- **Duplicate check before every add**: MemPalace has no upsert; duplicate drawers pollute semantic search
- **Cursor only on full commit**: Guarantees exactly-once processing semantics; partial failures are fully retryable