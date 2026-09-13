# Dream Cycle Procedure (Orient → Gather → Classify → File)

## Phase 1: Orient

### Checklist
- [ ] Read `~/.hermes/commons/data/ocas-lucid/config.json`
- [ ] Extract cursor (last-processed journal filename)
- [ ] Call `mempalace_status` to verify MemPalace availability
- [ ] Check hibernation: if no new journals for `hibernation_days` (default 7), skip with zero IO
- [ ] Load scoring configuration from config.json (thresholds, catchup_cap, exclude_self)

### Input
- config.json with fields: `cursor`, `hibernation_days`, `catchup_cap`, `exclude_self`, `scoring_thresholds`

### Output
- Validated config dict
- MemPalace status boolean
- Hibernation decision (skip/continue)
- Cursor value for comparison

---

## Phase 2: Gather

### Checklist
- [ ] Scan `~/.hermes/commons/journals/` for all `.json` journal files
- [ ] Exclude `ocas-lucid` own directory if `exclude_self: true`
- [ ] For each file, extract timestamp suffix `YYYYMMDDTHHMMSSZ` from filename
- [ ] Parse ISO-format timestamps with colons (e.g., `2026-07-27T13:59:01Z`)
- [ ] Compare lexicographically against cursor suffix
- [ ] Keep only files with suffix > cursor
- [ ] Cap results at `catchup_cap` (default 40)
- [ ] Sort by timestamp ascending (oldest first)

### Input
- Journal directory path
- Cursor filename (e.g., `mentor-light-20260726T104224Z.json`)
- catchup_cap integer
- exclude_self boolean

### Output
- List of journal file paths to process, sorted oldest-first, capped

---

## Phase 3: Classify

### Checklist
- [ ] For each journal, load JSON content
- [ ] Extract narrative text ONLY from priority fields:
  1. `decision.summary` / `decision.description`
  2. `decision.reasoning_summary`
  3. `action.side_effect_intent`
  4. `action.reason`
  5. `urgent_issues[].summary`
  6. `anomalies[].summary`
- [ ] Do NOT use payload dict keys, metrics fields, okr_evaluation, structured observation fields
- [ ] Apply scoring signals additively:
  - Decision keywords (+3): decided, confirmed, agreed, resolved, committed, approved, rejected
  - Entity density (+2): 3+ named entities in narrative text
  - Novel entities (+3): Entities not in MemPalace (check via mempalace_search)
  - Correction/lesson (+4): mistake, lesson, learned, corrected, wrong, fixed, should have (narrative only)
  - User-directed action (+3): Action taken on behalf of or directed by operator
  - Emotional signal (+2): frustrated, impressed, surprised, disappointed, pleased, grateful
  - Cross-skill reference (+2): Journal references entities from different skill domain
  - Relationship signal (+3): Relationship between people, or person ↔ project/organization
- [ ] Apply penalties:
  - Pure metrics (-3): Only numeric metrics, no narrative in decision field
  - Routine health check (-4): Source is ocas-custodian, event_type is routine health check
  - Duplicate content (-5): mempalace_check_duplicate match >0.9 similarity
- [ ] Thresholds: >=5 file, 3-4 skip+recirculate, <=2 skip
- [ ] Assign wing by source skill domain (see classification.md wing mapping)

### Input
- Journal JSON content
- MemPalace search function for novel entity check
- Duplicate check function

### Output
- Classification decision per journal: {file_path, score, decision: file|recirculate|skip, wing, room, kg_triples, narrative_for_filing}

---

## Phase 4: File

### Checklist
- [ ] For each filing decision (score >=5):
  - [ ] Call `mempalace_check_duplicate(content, threshold=0.9)` before filing
  - [ ] If not duplicate, call `mempalace_add_drawer(wing, room, content, source_file, added_by='mcp')`
  - [ ] For each KG triple identified: call `mempalace_kg_add(subject, predicate, object, valid_from, source_closet)`
  - [ ] Append DecisionRecord to `decisions.jsonl`
- [ ] Update `ingestion_log.jsonl` with run summary
- [ ] Write dream journal to `~/.hermes/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`
- [ ] Update config.json cursor to last processed journal filename
- [ ] Handle degraded mode (MemPalace unavailable): queue to `pending_mempalace.jsonl`

### Input
- Classification decisions from Phase 3
- MemPalace MCP tool functions

### Output
- Updated decisions.jsonl, ingestion_log.jsonl, config.json cursor
- Dream journal file
- Pending queue if degraded mode