---
name: ocas-lucid
description: >
  Nightly journal curator. Batch-processes OCAS skill journals into MemPalace's
  verbatim store via MCP tools. Runs as a scheduled cron job at 3am, classifying
  each journal for filing as a MemPalace drawer, MemPalace KG triple, Elephas
  Signal, or skip. Features re-emergence detection, two-pass stale handling,
  change magnitude gates, hibernation protection, and incremental cursor-based
  resumption. Use when: dream, lucid, nightly curation, journal consolidation,
  MemPalace filing, memory consolidation.
metadata:
  author: Indigo Karasu
  email: mx.indigo.karasu@gmail.com
  version: "2.0.1"
  hermes:
    tags: [memory, ingestion, dream-loop]
    category: memory
    cron:
      - name: "lucid:dream"
        schedule: "0 3 * * *"
        command: "lucid.dream"
      - name: "lucid:update"
        schedule: "0 0 * * *"
        command: "lucid.update"
  openclaw:
    skill_type: system
    visibility: public
    filesystem:
      read:
        - "{agent_root}/commons/journals/"
        - "{agent_root}/commons/data/ocas-lucid/"
        - "{agent_root}/commons/journals/ocas-lucid/"
      write:
        - "{agent_root}/commons/data/ocas-lucid/"
        - "{agent_root}/commons/journals/ocas-lucid/"
    self_update:
      source: "https://github.com/indigokarasu/lucid"
      mechanism: "version-checked tarball from GitHub via gh CLI"
      command: "lucid.update"
      requires_binaries: [gh, tar]
    requires:
      mcp:
        - name: "mempalace"
          description: "MemPalace MCP server for verbatim drawer storage and knowledge graph operations"
          required: true
    cron:
      - name: "lucid:dream"
        schedule: "0 3 * * *"
        command: "lucid.dream"
      - name: "lucid:update"
        schedule: "0 0 * * *"
        command: "lucid.update"
---

# Lucid

Nightly journal curator. Batch-processes journals from all OCAS skills into MemPalace's verbatim semantic store. Structured facts worth promoting to Chronicle are emitted as Signals to Elephas via the journal signal payload -- Lucid never writes to Chronicle or Weave directly.

## When to use

- Scheduled nightly cron at 3am (primary mode)
- Manual invocation via `lucid.dream` for immediate processing
- `lucid.status` to check last run, pending journals, filing stats

## When not to use

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

## Storage layout

```
{agent_root}/commons/data/ocas-lucid/
  config.json
  ingestion_log.jsonl
  decisions.jsonl
  recirculation_queue.jsonl
  removed_entries.jsonl
  staging/

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

### Phase 1: Orient

1. Read `config.json` for all settings
2. Read last dream record from `{agent_root}/commons/journals/ocas-lucid/` to see prior run summary
3. Read `ingestion_log.jsonl` to determine cursor position (last processed run_id per skill)
4. Call `mempalace_status` to verify MemPalace is available
5. Check hibernation: if no new journals exist across any skill for 7+ consecutive days, log skip and exit with zero IO
6. Count available unprocessed journals. If zero, enter skip path: run re-emergence check, surface one old memory, write abbreviated dream journal, exit

### Phase 2: Gather

1. Scan `{agent_root}/commons/journals/` across all skill directories for journal files newer than the cursor
2. Cap at 40 journals per run. If more exist, process oldest first; remainder picked up next cycle
3. Load recirculation queue: journals previously skipped that are due for re-evaluation (skip timestamp >= 7 days ago)
4. Read each journal file in full

### Phase 3: Classify

For each journal, compute a relevance score. Read `references/classification.md` for the full scoring model and filing taxonomy.

Four possible outcomes per journal:

**File to MemPalace drawer**: journal contains session context, reasoning, or narrative worth preserving verbatim. Select wing (source skill domain) and room (content topic). Check for duplicates via `mempalace_check_duplicate` before filing.

**File to MemPalace KG**: journal contains a temporal relationship or entity fact suitable for MemPalace's SQLite knowledge graph. Use `mempalace_kg_add` with validity window.

**Emit Signal to Elephas**: journal contains a structured entity or relationship meeting the confidence threshold for Chronicle promotion. Write Signal to the `signal` payload field in Lucid's own dream journal entry. One Signal per entity or relationship with sufficient confidence. See Signal schema in `spec-ocas-shared-schemas.md`.

**Skip**: journal is routine operational telemetry with no durable value. Log reason. Add to recirculation queue with current timestamp for future re-evaluation.

### Phase 4: File

Process each journal to completion before advancing:

1. Execute the filing decision (MemPalace MCP call, KG write, or Signal payload write)
2. On success: append DecisionRecord to `decisions.jsonl`
3. Update `ingestion_log.jsonl` with the processed run_id
4. Move to next journal

**MemPalace KG character restrictions (pitfall):** The `mempalace_kg_add` tool rejects `subject`, `predicate`, and `object` values containing special characters. Known failures:
- `/` (slash) in values like "House Music / DJing" → replace with "and" or remove
- `#` (hash) in values like "PR#213" → spell out as "PR 213"
- `:` (colon) in subjects like "elephas:deep" → replace with hyphen "elephas-deep"
- Parentheses, brackets, and other punctuation may also fail

Sanitize all KG field values before calling `mempalace_kg_add`. If a triple fails, retry with cleaned text rather than skipping.

**Journal path normalization (pitfall):** The config cursor may store paths in a nested format like `ocas-vesper/ocas-vesper/2026-04-10/file.json` while actual files live at `ocas-vesper/2026-04-10/file.json`. When building the processed set from the cursor, use only the filename portion as the dedup key, or normalize paths by stripping the duplicated directory segment. Otherwise previously-processed journals get re-scanned.

**Recirculation queue format inconsistency (pitfall):** Older entries in `recirculation_queue.jsonl` may use different field names (e.g., `skipped_at` vs `added_at` or missing entirely). When reading the queue, use `.get()` with a default rather than direct key access. If a timestamp field is missing, treat the entry as due for re-evaluation.

**Datetime timezone handling (pitfall):** When comparing recirculation queue timestamps against `datetime.utcnow()`, ensure both are either offset-aware or offset-naive. Use `datetime.now(timezone.utc)` for offset-aware comparisons, and parse incoming timestamps with `fromisoformat(... +00:00)` or add `tzinfo=timezone.utc` if missing.

**Cursor tracking (Gather phase note):** Build the processed-journal set from *both* `config.json` cursor AND `ingestion_log.jsonl`. The cursor only tracks the last batch's files, while the ingestion log has the full history. Missing this causes re-processing of previously handled journals.

After all journals processed:

5. Run re-emergence check (see below)
6. Run two-pass stale check (see below)
7. Write dream journal to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`

### Incremental cursor

The ingestion log tracks each processed run_id. If the session terminates mid-run, the next cycle resumes from the first unprocessed journal. Filed content and cursor updates are durable -- only the dream journal summary is lost on interruption.

## Re-emergence detection

Maintained in `removed_entries.jsonl`. Each skipped journal's key topics (entity names, concepts, domain) are recorded.

On every cycle, compare current journal topics against removed entries. If a topic that was previously skipped appears in 3+ subsequent journals, auto-promote it: file to MemPalace with elevated priority and remove from skip tracking. Log the re-emergence event in the dream journal.

Intuition: recurring topics are more important than they initially appeared.

## Two-pass stale handling

Applies to content Lucid previously filed in MemPalace, not to source journals.

If newer journal evidence contradicts a previously filed MemPalace entry:
- First encounter: mark as stale in `decisions.jsonl` with reason and contradicting evidence
- Second consecutive encounter (next run still contradicted): invalidate via `mempalace_kg_invalidate` or flag drawer for removal

Never delete on first contradiction. Two consecutive confirmations required.

## Change magnitude gates

Per-run safety check after classification, before filing:

- If >30% of scanned journals would be filed (unusually high): flag in dream journal as a warning, continue filing
- If >50% would be filed: pause. Write proposed filings to `{agent_root}/commons/data/ocas-lucid/staging/` as a review file. Do not file. Log the hold in decisions.jsonl. Notify operator.

## Hibernation protection

If no new journals have been written by any skill for 7 consecutive days, Lucid skips its cycle entirely with zero IO. On the first new journal after hibernation, run a full catch-up pass (still capped at 40 journals per run).

## Dream journal output

Journal type: Action (writes to MemPalace are external side effects).

Written to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json` using the standard JournalEntry schema with journal_spec_version "1.3".

Contents include:
- Total journals scanned, filed (by destination type), skipped
- Recirculation promotions and re-emergence events
- Change magnitude stats
- Stale items pending second-pass deletion
- Cumulative filing count, streak count, milestone flags
- One resurfaced old memory from MemPalace (>7 days old, randomly selected relevant filing)
- `signal` payload field: Signal files for any entities or relationships extracted during the run

On skip path (no new journals): abbreviated journal with re-emergence check result, resurfaced memory, and streak count.

## OKR evaluation

Universal OKRs per spec-ocas-journal.md, plus:

| OKR | Metric | Target | Window |
|-----|--------|--------|--------|
| Ingestion coverage | journals scanned / journals available | >= 0.99 | 30 runs |
| Duplicate avoidance | filings passing duplicate check without collision | >= 0.95 | 30 runs |
| Recirculation rate | recirculated items eventually filed / total recirculated | trend (no fixed target) | 30 runs |
| Signal emission precision | emitted Signals promoted by Elephas / total emitted | >= 0.80 | 30 runs |

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

## Background tasks

| Job name | Mechanism | Schedule | Command |
|----------|-----------|----------|---------|
| `lucid:dream` | cron | `0 3 * * *` (3am local) | `lucid.dream` |
| `lucid:update` | cron | `0 0 * * *` (midnight daily) | `lucid.update` |

Cron configuration: isolated session, light context. Operators with high journal volume (many active skills) may benefit from raising `max_turns` to 150 in their agent config.

No heartbeat entry. Lucid needs one substantial batch run per day, not lightweight polling.

## Platform notes

The 40-journal-per-run cap and incremental cursor keep turn count well within the default iteration budget. Each filing cycle (read journal → check duplicate → file → advance cursor) resets the activity-based timeout in Hermes v0.8+, so long runs complete naturally without inactivity timeouts.

If a session terminates mid-run, no filed work is lost. The cursor advances after each successful filing. The next run picks up from the first unprocessed journal.

## Ontology mapping

Lucid extracts no entities from user data directly. It classifies and routes journal content produced by other skills. When it emits Signals to Elephas, the Signal's `payload.type` reflects the entity type found in the source journal (Person, Place, Concept, etc.) per spec-ocas-ontology.md.

## Self-update

`lucid.update` pulls the latest package from the `source:` URL in this file's frontmatter. Runs silently — no output unless the version changed or an error occurred.

1. Read `source:` from frontmatter → extract `{owner}/{repo}` from URL
2. Read local version from SKILL.md frontmatter `metadata.version`
3. Fetch remote version: `gh api "repos/{owner}/{repo}/contents/SKILL.md" --jq '.content' | base64 -d | grep 'version:' | head -1 | sed 's/.*"\(.*\)".*/\1/'`
4. If remote version equals local version → stop silently
5. Download and install:
   ```bash
   TMPDIR=$(mktemp -d)
   gh api "repos/{owner}/{repo}/tarball/main" > "$TMPDIR/archive.tar.gz"
   mkdir "$TMPDIR/extracted"
   tar xzf "$TMPDIR/archive.tar.gz" -C "$TMPDIR/extracted" --strip-components=1
   cp -R "$TMPDIR/extracted/"* ./
   rm -rf "$TMPDIR"
   ```
6. On failure → retry once. If second attempt fails, report the error and stop.
7. Output exactly: `I updated Lucid from version {old} to {new}`

## Visibility

public

## Support file map

| File | When to read |
|------|-------------|
| `references/classification.md` | Before classifying any journal entry. Contains the relevance scoring model, filing taxonomy, wing/room assignment rules, and skip criteria. |
