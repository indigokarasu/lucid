# Skill Boundaries and Interfaces

Ownership rules and the read/write/query surface for the Lucid dream cycle.
Read this when deciding whether Lucid or an adjacent skill should handle a
task, or when wiring a new consumer of Lucid's output.

## Responsibility boundary

Lucid owns: nightly journal scanning, MemPalace filing (drawers + KG),
relevance classification, weak signal recirculation, re-emergence detection.

Lucid does **not** own:

| Concern | Owner |
|---------|-------|
| Chronicle writes | elephas-chronicle bridge pattern from the memory-system-design skill |
| Social graph updates | Weave only |
| Real-time pattern analysis | Corvus |
| Skill performance evaluation | Mentor |
| Entity identity resolution | Elephas |

## Adjacent boundaries

Elephas also reads journals, but for structured entity extraction and Chronicle
promotion. Lucid reads journals for verbatim preservation and semantic
searchability via MemPalace. When elephas is run manually (the `ocas-elephas`
skill is archived), update the `config.json` cursor to include new elephas
journal files — otherwise Lucid re-processes them and double-files.

### Elephas pipeline as a Lucid input source

The canonical `elephas_cron_run.py` writes run journals to
`<fs-root>/commons/journals/ocas-elephas/`, which is **not** in Lucid's scan
path. Other OCAS skills' journals (mentor, vesper, scout) that Elephas reads
from the shared `<fs-root>/commons/journals/` path **are** in Lucid's scope.

When running elephas directly (not via the `ocas-elephas` skill), see
`references/elephas-pipeline-gotchas.md` for the expected unprocessed residual
pattern and the nested entity extraction gap.

### Elephas JSON parse errors

`elephas_cron_pipeline.py` skips ~43% of `mentor-light-*` files due to
malformed JSON (trailing commas, unescaped newlines in `notes` fields). This
is a **producer-side bug in `ocas-mentor`**, not an elephas pipeline bug. Lucid
handles it gracefully via try/except. See
`references/elephas-pipeline-json-errors.md` for the full error pattern, root
cause, and recommended non-mitigation.

## Optional skill cooperation

- **Elephas**: Lucid queries Chronicle via `elephas.query` to check whether an
  entity already exists before emitting a Signal. If Elephas is unavailable,
  Lucid emits the Signal anyway — Elephas deduplicates on ingestion.
- **MemPalace**: **Required.** Lucid uses MemPalace MCP tools for all filing
  operations. If MemPalace is unavailable, Lucid logs failures and skips filing
  for that run (degraded mode; classification is still recorded).

## Inter-skill interfaces

**Reads (all read-only):**

- All skill journals from `{agent_root}/commons/journals/` (same access
  pattern as Mentor and Elephas)

**Writes:**

- MemPalace drawers and KG via MCP tools (external)
- Signal payload field in Lucid's own dream journal (standard Signal schema
  from `spec-ocas-shared-schemas.md`)
- Lucid's own journal, data, and decisions files only

**Queries:**

- Read: `mempalace_status`, `mempalace_search`, `mempalace_check_duplicate`,
  `mempalace_get_taxonomy`
- Write: `mempalace_add_drawer`, `mempalace_kg_add`, `mempalace_kg_invalidate`
- Optional: `elephas.query` (pre-emission entity existence check)

## Ontology mapping

Lucid extracts no entities from user data directly. It classifies and routes
journal content produced by other skills. When it emits Signals to Elephas, the
Signal's `payload.type` reflects the entity type found in the source journal
(Person, Place, Concept, etc.) per `spec-ocas-ontology.md`.

## Visibility

public
