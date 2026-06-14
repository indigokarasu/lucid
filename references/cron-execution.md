# Cron Execution Context

## Heredoc Python Pattern

When running in cron context, `execute_code` is blocked. Use heredoc Python via `terminal()` for any inline data processing:

```bash
python3 -c "
import json, sys
# ... logic here
"
```

For multi-step pipelines, chain with `&&` or write a temp script to `/tmp/` and execute it.

## Two-Pass Classification Workflow

In cron context, classification must work without `execute_code`:

1. **Pass 1 — Journal discovery**: Use `terminal(find ...)` with `-newermt` and `-name` filters to enumerate JSON journals. Cross-reference against the ingestion log's processed set (see `references/gotchas.md` for the full dedup pipeline).
2. **Pass 2 — Relevance scoring**: Read each journal file via `read_file`, apply the scoring model from `references/classification.md`, and determine the filing path. Write decisions to `decisions.jsonl` via `terminal(tee -a ...)`.

## Degraded Mode Decision Tree

When running in cron context:

1. Check MemPalace MCP availability by calling `mempalace_status`.
2. **If MemPalace is unavailable**: Log `degraded: mempalace` to the evidence file. Skip all filing operations. Queue the run's decisions for retry on the next cycle.
3. **If journal sources are missing**: Continue with available sources. Log which sources were skipped.
4. **If ingestion log is unreadable**: Treat as fresh run (no cursor). Process all discovered journals.

## Cron-Specific Constraints

- No interactive prompts. All decisions must be deterministic.
- No `execute_code` tool. Use `terminal()` with heredoc Python or shell pipelines.
- No `clarify` tool. Default to `lucid.dream` when invoked from cron.
- Write progress to the evidence file after each phase so partial progress is recoverable.
