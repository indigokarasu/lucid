---
name: ocas-lucid
description: >
  Schedules a nightly (3am) dream loop to review session interactions and intelligently decide what new information should be stored in MemPalace and Chronicle. Uses a dual-phase process (Fresh Scan and Weak Signal Recirculation) to ensure that evolving context promotes weak signals into strong memory over time. Runs via background=true to avoid timeout on long-running analysis.
metadata:
  author: Indigo Karasu
  email: mx.indigo.karasu@gmail.com
  version: "1.0.0"
  hermes:
    tags: [memory, ingestion, dream-loop]
    category: evolution
    cron:
      - name: "lucid:dream"
        schedule: "0 3 * * *"
        command: "lucid.dream"
  openclaw:
    skill_type: system
    visibility: public
    filesystem:
      read:
        - "{agent_root}/commons/journals/"
        - "{agent_root}/commons/journals/ocas-lucid/"
      write:
        - "{agent_root}/commons/journals/ocas-lucid/"
        - "{agent_root}/commons/data/ocas-lucid/"
    self_update:
      source: "https://github.com/indigokarasu/lucid"
      mechanism: "version-checked tarball from GitHub via gh CLI"
      command: "lucid.update"
      requires_binaries: [gh, tar, python3]
    cron:
      - name: "lucid:dream"
        schedule: "0 3 * * *"
        command: "lucid.dream"
      - name: "lucid:update"
        schedule: "0 0 * * *"
        command: "lucid.update"
---

# Lucid

Lucid is the system's nocturnal curatorial engine — a nightly dream loop that reviews the day's interactions across all skills and journals, then intelligently decides what new information deserves to be stored in MemPalace (documented detail) and Chronicle (atomic facts and relationships).

By running as a background process (`background=true` with `notify_on_complete=true`), Lucid avoids terminal timeouts on long-running analysis across thousands of journal entries.

Lucid does not block or interfere with daytime operations — it operates in complete isolation, consuming only read access to journals, and produces journal entries documenting its decisions.

---

## When to use

- Review daily interactions for MemPalace/Chronicle ingestion candidates
- Identify patterns, decisions, or relationships missed during real-time tool usage
- Automate the "curator" role: filter noise, extract signal, route to correct storage
- Create "tunnels" between wings/rooms by linking related entities across domains

---

## When not to use

- Web research or user queries — use Sift or other context-aware skills
- Real-time memory filing — this is for batch, reflective ingestion
- Skill building or improvement — use Forge and Mentor

---

## Responsibility boundary

Lucid owns:

- Daily ingestion candidate discovery across all skill journals
- Intelligent routing decisions (MemPalace drawer vs Chronicle triple)
- Automatic filing via MCP tools or skill invocation
- Journal logging of ingestion decisions

Lucid does not own:

- Real-time tool call routing — this happens during active sessions
- Skill evaluation or improvement proposals — this is Mentor's domain
- Behavioral pattern detection — this is Corvus's domain

---

## Storage layout

```
{agent_root}/commons/journals/ocas-lucid/
  YYYY-MM-DD/
    {run_id}.json

{agent_root}/commons/data/ocas-lucid/
  ingestion_log.jsonl
  decisions.jsonl
```

---

## Initialization

On first invocation, create:

1. `{agent_root}/commons/journals/ocas-lucid/` (with today's date subdirectory)
2. `{agent_root}/commons/data/ocas-lucid/`
3. Empty `ingestion_log.jsonl` and `decisions.jsonl`
4. Register cron job `lucid:dream` (3am nightly) if not already present

---

## Commands

- `lucid.dream` — run the nightly dream loop: ingest journals, decide, file, journal
- `lucid.status` — current state: last run timestamp, pending decisions, total files processed
- `lucid.update` — pull latest from GitHub source; preserves journals and data

---

## Ingestion pipeline

1. **Scanning Phase**
   - Fresh Scan: Read all new journals from `{agent_root}/commons/journals/` since the last successful run.
   - Recirculation: Every 7 days, re-scan journal entries that were previously "skipped" to see if new context has promoted them to "strong signals."
   - Use `ingestion_log.jsonl` to track processing status and timestamp for every file.

2. **Analysis Phase**
   - For each entry, calculate a relevance score based on entity relevance, decision keywords, and age.
   - Classify:
     - **Decision Record** $\rightarrow$ Chronicle (Subject $\rightarrow$ Predicate $\rightarrow$ Object)
     - ** Specification/Data** $\rightarrow$ MemPalace Drawer (Wing/Room based on context)
     - **Reflection** $\rightarrow$ AAAK Diary (MemPalace)
   - Check for duplicates via `mempalace_check_duplicate` before filing.
   - Perform a "Topical Drift" check for recirculated entries: query the KG for entities mentioned in the entry to see if they have since become relevant.

3. **Routing Decision**
   - Is this a fact about relationships? → Chronicle
   - Is this verbatim content that needs exact phrasing? → MemPalace Drawer
   - Is this a personal observation or meta-reflection? → AAAK Diary

4. **Filing Phase**
   - Call `mempalace_kg_add` for Chronicle facts
   - Call `mempalace_add_drawer` for verbatim content
   - Call `mempalace_diary_write` for AAAK entries
   - Log success/failure to `decisions.jsonl`

5. **Journal Phase**
   - Write summary journal entry to `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`
   - Include: total entries scanned, entries filed, failures, notable discoveries

---

## Safety invariants

- Never file duplicate content (check before filing)
- Never overwrite existing drawers (check `mempalace_check_duplicate`)
- Log all failures to `decisions.jsonl` for later manual review
- Use `background=true` for the entire pipeline to avoid timeout

---

## Inter-skill interfaces

Lucid consumes:

- All skill journals from `{agent_root}/commons/journals/` (read-only scan)
- MemPalace MCP tools for filing (read checks, write actions)

Lucid produces:

- Journal entries to its own directory (`ocas-lucid/YYYY-MM-DD/`)
- Journal entries to global journal directory for other skills to consume
- Updates to MemPalace (Chronicle and document drawers)

---

## Nightly cron job (lucid:dream)

| Job name | Mechanism | Schedule | Command |
|---|---|---|---|
| `lucid:dream` | cron | `0 3 * * *` (3am local) | `lucid.dream` — full daily dream loop |

Cron options: `sessionTarget: isolated`, `lightContext: true`, `wakeMode: next-heartbeat`.

Registration during `lucid.init`:

```
# Check platform scheduling registry for existing tasks
# Task declared in SKILL.md frontmatter metadata.{platform}.cron
# If lucid:dream absent:
#   register via platform cron API
```

---

## Self-update

`lucid.update` pulls the latest package from the GitHub source defined in the frontmatter. Runs silently — no output unless version changed or error occurred.

1. Read `source:` from frontmatter → extract `{owner}/{repo}`
2. Read local version from `metadata.version`
3. Fetch remote version: `gh api "repos/{owner}/{repo}/contents/SKILL.md" --jq '.content' | base64 -d | grep 'version:' | head -1 | sed 's/.*\"\\(.*\\)\".*/\\1/'`
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

---

## Visibility

public

---

## Journal output

Every run writes a summary journal with the following schema:

```json
{
  "run_id": "YYYYMMDD-HHmmss",
  "date": "YYYY-MM-DD",
  "entities_scanned": N,
  "entities_filed": N,
  "failures": N,
  "notable_discoveries": ["fact1", "fact2"],
  "top_domains": ["wing1: count", "wing2: count"]
}
```

This journal is written to both:
- `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/{run_id}.json`
- `{agent_root}/commons/journals/YYYY-MM-DD/ocas-lucid-{run_id}.json`

---

## Example: Ingestion Decision Flow

**Scenario:** During a session, I discover that "Hermes Agent uses GPT-4o-mini for its CLI mode."

**Real-time:** I may not file it immediately.

**Lucid (nightly):**
1. Reads journal entry containing the phrase "GPT-4o-mini"
2. Classifies it as a system fact with relationship potential
3. Routes to Chronicle:
   - Subject: `Hermes Agent`
   - Predicate: `uses_model`
   - Object: `GPT-4o-mini`
4. Files via `mempalace_kg_add`
5. Logs success to `decisions.jsonl`

**Result:** Future queries about Hermes Agent's models now return this fact automatically.
