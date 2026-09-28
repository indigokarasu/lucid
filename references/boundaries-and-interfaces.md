# Skill Boundaries and Interfaces

Ownership rules and the read/write/query surface for the Lucid curation cycle.

## Responsibility boundary

Lucid owns:

- nightly read-only scanning of OCAS journals;
- relevance classification;
- recirculation and re-emergence detection;
- provider-independent curated journal artifacts;
- optional principal-scoped memory candidates when the source journal already carries an explicit principal.

Lucid does not own:

| Concern | Owner |
|---|---|
| Durable memory acceptance, contradiction handling, retrieval, correction, forgetting | Chronicle |
| Agent autobiographical identity and self-dreaming | Agent autobiographical growth subsystem |
| Agent behavioral adaptation | Praxis |
| Social graph updates | Weave |
| Skill performance evaluation | Mentor |

## Journal boundary

Lucid reads source journals as immutable evidence. It never edits or deletes them.

A curated Lucid journal is a derived evidence artifact, not proof that durable memory was accepted.

If the source journal has no explicit principal, Lucid writes the curated artifact with no memory candidate. It MUST NOT infer that the user is the owner.

## Chronicle boundary

Lucid does not open Chronicle's database and does not call a private storage API.

When a source journal carries an explicit principal, Lucid may attach a principal-scoped candidate to the curated artifact. Sanctioned Chronicle ingestion independently decides whether and how to persist it.

A Chronicle outage therefore does not invalidate Lucid's classification work. The curated artifact remains retryable evidence.

## User vs agent memory

User-directed curation and agent autobiography remain separate.

- User-owned candidates require user-grounded provenance and an explicit user principal.
- Agent-owned journals may be curated as evidence but are never silently converted into user memory.
- Agent autobiographical consumers may read agent-owned journal evidence through documented journal interfaces.

## Inter-component interfaces

Reads:

- `{agent_root}/commons/journals/**` read-only;
- Lucid's own config, decision, evidence and ingestion state.

Writes:

- `{agent_root}/commons/data/ocas-lucid/**`;
- `{agent_root}/commons/journals/ocas-lucid/YYYY-MM-DD/**`.

Lucid never writes another component's private data directory.

## Candidate fields

A memory candidate includes at minimum:

- target principal;
- claim state;
- derivation type;
- confidence;
- source component;
- source journal;
- source provenance.

Repeated summaries of one source remain one evidence lineage.

## Failure semantics

- malformed source journal: record read error and continue;
- curated artifact write failure: do not claim successful filing for that source;
- Chronicle unavailable: non-fatal to Lucid; downstream ingestion retries separately;
- missing principal: curate evidence with `memory_candidate: null`.

## Correlation

Curated artifacts preserve source journal path and run id. Multi-component workflows should also preserve correlation/causation ids when present in the source.
