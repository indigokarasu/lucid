# Dream Journal Schema

## Entry Format
```
Date: YYYY-MM-DD
Type: [observation-derived | memory-synthesis | anomaly]
Content: [150-350 word dream recollection]
Source: [source observation file]
Confidence: [low | medium | high]
```

## Full Journal Entry Schema (JournalEntry v1.3)
```json
{
  "journal_spec_version": "1.3",
  "run_id": "lucid-YYYYMMDDTHHMMSSZ",
  "timestamp": "ISO8601 with timezone",
  "mode": "normal | degraded: mempalace",
  "mempalace_available": true | false,
  "mempalace_actual_calls": N,
  "scan_count": N,
  "file_count": N,
  "recirculate_count": N,
  "skip_count": N,
  "reemergence_events": [...],
  "signals": [...],
  "pending_mempalace": N,
  "skip_path": "explanation if mode=degraded"
}
```

## Signal Schema
```json
{
  "type": "elephas_signal",
  "source_journal": "rel/path/to/journal.json",
  "subject": "entity name",
  "predicate": "relationship type",
  "object": "related entity",
  "confidence": "low | medium | high",
  "payload_type": "Person | Place | Event | Concept"
}
```