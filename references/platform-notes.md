# Platform-Specific Execution Notes

## Cron Execution (Primary Mode)

- **Schedule**: 03:00 local time daily (configured in Hermes cron)
- **Environment**: Hermes agent profile `indigo`, working directory `~/.hermes/profiles/indigo`
- **Command**: `hermes skill run ocas-lucid -- nightly`
- **Timeout**: 180 seconds (configured in cron job)
- **Logs**: Cron captures stdout/stderr to job log; dream journal is primary artifact

### Cron-Specific Behaviors
- No interactive input available — all prompts must have defaults
- `--help` must exit 0 without side effects (scripts must guard)
- Exit codes: 0=success, 1=general error, 2=usage error, 3=dependency missing, 4=MemPalace unavailable (degraded)
- Stdout: structured JSON summary for log aggregation
- Stderr: diagnostics, warnings, errors

---

## Manual Invocation (`lucid.dream`)

- **Trigger**: User types `/lucid.dream` in Hermes TUI or CLI
- **Bypasses**: Hibernation check (always runs)
- **Flags**:
  - `--force` — process all journals since epoch (ignore cursor)
  - `--since YYYYMMDD` — process journals after date
  - `--dry-run` — scan and classify only, no filing, no cursor update
  - `--json` — emit structured JSON to stdout

---

## Degraded Mode Behavior by Platform

| Platform | MemPalace Path | Degraded Trigger |
|----------|---------------|------------------|
| Linux (VPS) | `~/.mempalace/palace` | Directory missing, permission denied, MCP import fails |
| macOS | `~/Library/Application Support/mempalace/palace` | Same |
| Windows | `%APPDATA%\mempalace\palace` | Same |

**Detection**: `tool_status()` raises exception or returns `available: false`

---

## Configuration File Locations

| File | Linux | macOS | Windows |
|------|-------|-------|---------|
| config.json | `~/.hermes/commons/data/ocas-lucid/config.json` | Same | `%USERPROFILE%\.hermes\commons\data\ocas-lucid\config.json` |
| journals | `~/.hermes/commons/journals/` | Same | `%USERPROFILE%\.hermes\commons\journals\` |
| MemPalace palace | `~/.mempalace/palace` | `~/Library/Application Support/mempalace/palace` | `%APPDATA%\mempalace\palace` |

---

## Python Environment

- **Runtime**: Hermes-managed venv at `~/.hermes/venv` (Linux/macOS) or embedded Python
- **Dependencies**: `mempalace` package must be installed in Hermes venv
- **Import path**: `from mempalace.mcp_server import ...` (not MCP protocol)
- **Version pin**: `mempalace>=0.3.0` (breaking changes in 0.4+)

---

## File System Considerations

- Journal filenames use UTC timestamps (`Z` suffix) for consistent lexicographic ordering across timezones
- Directory dates (`YYYY-MM-DD/`) are local timezone — do NOT use for ordering
- Symlinks in journal tree: follow (journals may be linked from skill repos)
- Permission model: all files owned by agent user, mode 0600 for configs, 0644 for journals

---

## Signal Integration

Lucid emits signals for downstream consumers (Elephas, Mentor, Corvus):

| Signal Type | Emitted When | Consumer |
|-------------|--------------|----------|
| `elephas_signal` | KG triple filed | Elephas (Chronicle ingestion) |
| `okr_evaluation` | Quarterly OKR eval | Mentor (skill improvement) |
| `reemergence_event` | Recirculated journal promoted | Corvus (pattern detection) |
| `anomaly` | Duplicate spike, hibernation false skip | Corvus, Mentor |

Signals written to dream journal `signals` array; Elephas reads dream journals during its ingestion cycle.