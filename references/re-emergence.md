# Re-Emergence Detection & Two-Pass Stale Handling

## Purpose
Detect previously skipped journals that now have relevance due to new context (new entities, relationships, or corrections in MemPalace). Prevents permanent loss of weak signals.

## Two-Pass Algorithm

### Pass 1: Recirculation Queue Scan
- Read `recirculation_queue.jsonl` (journals scored 3-4 from previous runs)
- For each entry, extract the source journal path and original score
- Check if enough time has passed (config: `reemergence_min_days`, default 14)

### Pass 2: Re-Scoring with Current MemPalace State
- For each eligible recirculated journal:
  - Reload the original journal JSON
  - Re-extract narrative text (same priority fields as Phase 3)
  - Re-score using **current** MemPalace state (novel entity check, duplicate check against current palace)
  - Apply same thresholds: >=5 file, 3-4 recirculate (re-queue), <=2 skip
  - If now >=5: file immediately (Phase 4)
  - If still 3-4: update recirculation_queue.jsonl with new timestamp
  - If now <=2: move to `removed_entries.jsonl` with reason

## Triggers for Re-Emergence
- New entity added to MemPalace that matches journal content (novel entity signal flips from 0 to +3)
- Relationship established that connects previously isolated entities (+3 relationship signal)
- Correction/lesson in MemPalace that contextualizes a prior ambiguous entry
- Cross-skill reference now resolvable (previously unknown skill domain now in palace)

## Configuration
```json
{
  "reemergence_min_days": 14,
  "reemergence_max_queue_size": 200,
  "reemergence_batch_size": 20
}
```

## Outputs
- Updated `recirculation_queue.jsonl` (re-queued entries with new timestamps)
- `removed_entries.jsonl` (permanently skipped with reason)
- New filings via Phase 4 for promoted entries
- Dream journal signal entries for each re-emergence event