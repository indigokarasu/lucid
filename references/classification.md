# Classification Reference
# (Supersedes the full copy in SKILL.md body; kept for detailed scoring model reference)

## Relevance scoring
Each journal receives a numeric score. Thresholds: >=5 file, 3-4 recirculate, <=2 skip.

### Content extraction for scoring
**CRITICAL**: Extract text ONLY from narrative fields. Do NOT serialize the entire journal JSON (including payload dictionary keys). Payload key names like `lessons_extracted`, `events_recorded`, `signals_created` contain scoring-triggering words that are NOT narrative content.

**COUNT-SUMMARY FALSE POSITIVE**: Journals reporting ingest counts (e.g., "Ingest complete: 7 journals scanned, 1 new events, 9 new lessons") contain "lessons" as a metric count, not narrative. The `correction_or_lesson(+4)` signal must NOT fire on these.

**Narrative fields** (priority order):
1. decision.summary / decision.description
2. decision.reasoning_summary
3. action.side_effect_intent
4. action.reason
5. urgent_issues[].summary
6. anomalies[].summary

**Do NOT use for scoring**: payload dict keys, metrics fields, okr_evaluation, structured observation fields.

### Scoring signals (additive)
| Signal | Points | Detection |
|--------|--------|-----------|
| Decision keywords | +3 | decided, confirmed, agreed, resolved, committed, approved, rejected |
| Entity density | +2 | 3+ named entities in narrative text only |
| Novel entities | +3 | Entities not yet in MemPalace (check via mempalace_search) |
| Correction/lesson | +4 | mistake, lesson, learned, corrected, wrong, fixed, should have (narrative only) |
| User-directed action | +3 | Action taken on behalf of or directed by operator |
| Emotional signal | +2 | frustrated, impressed, surprised, disappointed, pleased, grateful |
| Cross-skill reference | +2 | Journal references entities from a different skill's domain |
| Relationship signal | +3 | Relationship between people, or person ↔ project/organization |

### Penalties (subtractive)
| Signal | Points | Detection |
|--------|--------|-----------|
| Pure metrics | -3 | Only numeric metrics, no narrative in decision field |
| Routine health check | -4 | Source is ocas-custodian, event_type is routine health check |
| Duplicate content | -5 | mempalace_check_duplicate match >0.9 similarity |

## Filing taxonomy
### MemPalace drawer (verbatim filing)
File when journal contains session reasoning, tradeoffs, workflow narrative, research findings, or lessons learned with context. Extract narrative content from decision/action fields — do NOT file the full raw JSON.

### MemPalace KG (relationship filing)
File when journal contains factual relationships, temporal state changes, or entity attributes. Use mempalace_kg_add with sanitized subject/predicate/object (snake_case predicates).

### Wing/room assignment
Source skill domain maps to wing (see SKILL.md). If mempalace_list_wings returns only root, file into root/<wing_topic>. Prefer merging into existing rooms over creating near-duplicates.