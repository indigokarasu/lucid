# ☀️ Lucid

> **Nightly journal curator — batch-processes skill journals into MemPalace's verifiable memory store.**

## Why Lucid?

Every skill generates journals — records of what happened, what was learned, what went wrong. Lucid processes these nightly, classifying each entry for filing as a drawer, knowledge graph triple, Elephas Signal, or skip. It's the bridge between raw skill output and permanent, queryable memory.

Skill packages follow the [agentskills.io](https://agentskills.io/specification) open standard and are compatible with OpenClaw, Hermes Agent, Claude, and any agentskills.io-complified client.

## Quick Start

```
# Check what was curated
"What did Lucid process last night?"

# Run manually
"Run the journal curation now"
```

Lucid auto-initializes on first use, registering the nightly 3am cron job.

## What It Does

Lucid batch-processes OCAS skill journals into MemPalace's verbatim store each night. It classifies each entry for filing as a drawer, knowledge graph triple, Elephas Signal, or skip. This is how daily skill activity becomes permanent, searchable memory.

## Dependencies

- All skills — reads journals from all
- [Elephas](https://github.com/indigokarasu/elephas) — receives Signal files for Chronicle
- MemPalace MCP tools

---

*Lucid is part of the [OCAS Agent Suite](https://github.com/indigokarasu).*