# Skill Boundaries and Interfaces

Ownership rules and the read/write/query surface for the Lucid dream cycle.
Read this when deciding whether Lucid or an adjacent skill should handle a
task, or when wiring a new consumer of Lucid's output.

## Responsibility boundary

Legacy Lucid owns: nightly journal scanning, legacy MemPalace filing (drawers + KG),
relevance classification, weak signal recirculation, and re-emergence detection.

The `dreaming/` package is shared infrastructure with hard-separated
`relationship` and `self` namespaces. Domain ownership remains elsewhere.

Lucid does **not** own:

| Concern | Owner |
|---------|-------|
| Canonical interaction/world evidence | Chronicle |
| User interaction-pattern evidence | Chronicle |
| Relationship posture/adaptation | Dreaming relationship domain |
| Indigo identity evolution | Autobio/SOUL |
| Social graph updates | Weave only |
| Skill performance evaluation | Mentor |
| Entity identity resolution | Chronicle |

## Adjacent boundaries

Chronicle is the active canonical memory/evidence system. Relationship Dreaming
may consume Chronicle event ids and descriptive interaction patterns but does
not write user facts back as relationship policy.

Historical Elephas/MemPalace integration notes below are retained only for
legacy-curator recovery. Elephas is not an active owner in the current
architecture.

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

## Optional / legacy cooperation

- **Chronicle**: the new Dreaming relationship adapter consumes Chronicle's
  descriptive interaction patterns and authoritative event ids.
- **Autobio**: the new Dreaming self adapter stages Autobio observation ids in
  the self namespace; it never writes SOUL.
- **MemPalace / Elephas**: legacy-curator dependencies only. They are not
  current architecture owners and new Dreaming code must not depend on them.

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
