# Shared Dreaming Kernel

Lucid now contains the portable OCAS Dreaming kernel under `dreaming/`.

This is a migration boundary, not a claim that the legacy MemPalace journal
curator and the new Dreaming system are the same responsibility.

## Two domains, one implementation

The kernel is reusable infrastructure with two hard-separated namespaces:

- `relationship` — evidence-backed learning about how the agent should work
  with a particular user. Chronicle interaction patterns may seed candidates.
- `self` — evidence-backed reflection about the agent's own behavior.
  Autobio may seed candidates; Autobio/SOUL remains the authority that decides
  whether a promoted self insight becomes identity.

A candidate from one domain cannot be promoted by the other domain's kernel.
The JSON store writes one file per domain.

## Promotion contract

Model or heuristic reflection may propose candidates, but it cannot activate
them directly.

```
evidence -> candidate -> gate decision -> promoted state
```

`hold` and `block` never modify active state. `promote` is converted to
`block` when the candidate has no authoritative evidence references.

## Chronicle boundary

`dreaming.chronicle.ChroniclePatternSource` reads
`ChronicleCore.interaction_patterns`. Chronicle remains descriptive: it emits
recurrence, confidence and event ids, not behavioral policy.

Relationship Dreaming is responsible for interpreting those observations into
scoped relationship posture and, in later stages, measuring whether an
adaptation actually helped.

## Autobio boundary

`dreaming.autobio.propose_self_observation` creates a self-domain candidate
from an Autobio observation id.

The adapter does not edit `SOUL.md`. Autobio remains the sole owner of Indigo
identity evolution and its existing framing contract ("Indigo is not Jared").

## Legacy Lucid curator

The existing `lucid.dream` journal-curation cycle remains available during
migration. It is a legacy compatibility surface and must not be expanded into
user modeling or identity mutation. Its useful operational mechanics
(cursoring, re-emergence, stale-signal handling, duplicate avoidance and
recovery) may be migrated into their owning systems over time.
