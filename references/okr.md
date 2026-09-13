# OKR Evaluation Reference

## Purpose
Evaluate Lucid's nightly runs against Objectives and Key Results. Runs during dream cycle post-file phase.

## Current OKRs (Updated Quarterly)

### Objective: Maximize signal capture from OCAS skill journals
- KR1: Filing rate ≥ 15% of scanned journals (file_count / scan_count)
- KR2: Re-emergence promotion rate ≥ 10% of recirculation queue per quarter
- KR3: Zero data loss events (cursor rollback, skipped journals without decision)

### Objective: Maintain MemPalace semantic quality
- KR4: Duplicate filing rate ≤ 1% (duplicate skips / file_count)
- KR5: KG triple density ≥ 0.5 per drawer filing (kg_triples / file_count)
- KR6: Wing/room consolidation — new room creation rate ≤ 5% of filings

### Objective: Operational reliability
- KR7: Successful run rate ≥ 99% (runs without degraded mode / total runs)
- KR8: Dream cycle latency ≤ 120 seconds (p95)
- KR9: Hibernation accuracy — zero false hibernation skips when journals exist

## Evaluation Procedure

Run after Phase 4 completes, before dream journal write:

1. Load current OKR config from `config.json` → `okr` section
2. Compute metrics from `ingestion_log.jsonl` (last 90 entries = ~quarter)
3. Score each KR: met (1.0), partial (0.5), missed (0.0)
4. Aggregate: OKR score = mean(KR scores)
5. Write OKR evaluation to dream journal `signals` array with type `okr_evaluation`
6. If OKR score < 0.7: append alert to `evidence.jsonl` for Mentor review

## Metrics Sources

| Metric | Source |
|--------|--------|
| scan_count, file_count, recirculate_count, skip_count | ingestion_log.jsonl |
| duplicate skips | decisions.jsonl (duplicate: true) |
| kg_triples | decisions.jsonl (kg_triples array length) |
| new room creations | mempalace_status diff or decisions.jsonl room field |
| run latency | ingestion_log.jsonl timestamp diff |
| degraded mode | dream journal mode field |

## OKR Config Schema (config.json)

```json
{
  "okr": {
    "filing_rate_target": 0.15,
    "reemergence_promotion_target": 0.10,
    "duplicate_rate_max": 0.01,
    "kg_density_target": 0.5,
    "new_room_rate_max": 0.05,
    "success_rate_target": 0.99,
    "latency_p95_max_seconds": 120,
    "evaluation_window_entries": 90
  }
}
```

## Output Signal Schema

```json
{
  "type": "okr_evaluation",
  "timestamp": "ISO8601",
  "okr_score": 0.0-1.0,
  "kr_scores": {
    "filing_rate": 1.0,
    "reemergence_promotion": 0.5,
    "duplicate_rate": 1.0,
    "kg_density": 1.0,
    "new_room_rate": 1.0,
    "success_rate": 1.0,
    "latency": 1.0,
    "hibernation_accuracy": 1.0
  },
  "alert": true/false
}
```