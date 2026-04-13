# ocas-lucid skill package

## Files

- `SKILL.md` — Skill specification with YAML frontmatter, commands, and operational rules
- `REFERENCES/init-script.py` — Initialization logic (creates directories, log files)
- `REFERENCES/dream-loop.py` — Main dream loop pipeline (scans journals, classifies, files)
- `REFERENCES/cron-command.sh` — Cron entry point, invokes dream loop in background

## Architecture

### How it avoids timeout

The dream loop spawns as a **background process** using `subprocess.Popen([...], env=os.environ)`. This detaches execution from the current tool call, allowing it to run indefinitely without hitting the 5-minute timeout.

### Storage layout

```
/root/.hermes/commons/
  journals/ocas-lucid/
    YYYY-MM-DD/
      {run_id}.json
  data/ocas-lucid/
    ingestion_log.jsonl   # Tracks last successful run
    decisions.jsonl       # Logs all filing decisions (success/failure)
```

### Cron registration

The SKILL.md frontmatter defines the cron job:
```yaml
metadata:
  hermes:
    cron:
      - name: "lucid:dream"
        schedule: "0 3 * * *"
        command: "lucid.dream"
```

When `lucid.init` runs (via skill initialization) or on first invocation, the cron job is registered via the platform's scheduling API.

### Nightly flow (3am daily)

1. **Cron triggers** → invokes `lucid.dream`
2. **Background spawn** → `dream-loop.py` detaches via `subprocess.Popen`
3. **Scans journals** → reads all `*.json` files in `{agent_root}/commons/journals/`
4. **Classifies** → decides MemPalace vs Chronicle vs Skip
5. **Files** → calls `mempalace_kg_add` or `mempalace_add_drawer`
6. **Logs** → appends to `decisions.jsonl`, updates `ingestion_log.jsonl`
7. **Notifies** → `notify_on_complete=true` sends final summary to origin

### Why this design works

- **Non-blocking**: Background subprocess ensures the cron job returns immediately, avoiding platform timeout
- **Idempotent**: Uses `ingestion_log.jsonl` to track processed days; no re-processing
- **Resilient**: Logs failures to `decisions.jsonl` for later manual review
- **Extensible**: New classification rules can be added without touching the core loop

## Usage

### Manual invocation

```bash
# After skill installation
lucid.dream
```

### View status

```bash
# Check last run date and decision statistics
cat ~/.hermes/commons/data/ocas-lucid/decisions.jsonl | tail -n20
```

### Manually re-run

```bash
# Reset the ingestion log to force a re-run
echo '{"last_run_date": "2026-04-12"}' > ~/.hermes/commons/data/ocas-lucid/ingestion_log.jsonl
lucid.dream
```

## Notes

- If MemPalace is not configured or unavailable, the dream loop skips filing and logs failures to `decisions.jsonl`
- The loop only processes journals with a `"date"` field ≥ the last run date
- Empty or malformed journal entries are skipped silently; errors are logged
