# Shared Dreaming Kernel

Lucid is the canonical home of the OCAS Dreaming kernel under `dreaming/`.

The historical journal curator is a legacy compatibility path (`lucid.curate`), not a separate owner of Dreaming.

## Two domains, one implementation

The kernel is reusable infrastructure with two hard-separated namespaces:

- `relationship` — evidence-backed staging of user-owned relationship interpretations. Chronicle interaction patterns may seed candidates; promoted kernel state is not canonical memory or direct behavioral authority.
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

The relationship domain stages interpretations for the User Dreaming contract. Durable accepted results belong to the user principal and must be written through Chronicle's sanctioned contract; any runtime relationship hint is a rebuildable projection from verified user-owned state, not a direct agent behavior shift.

## Autobio boundary

`dreaming.autobio.propose_self_observation` creates a self-domain candidate
from an Autobio observation id.

The adapter does not edit `SOUL.md`. Autobio remains the sole owner of Indigo
identity evolution and its existing framing contract ("Indigo is not Jared").

## Legacy Lucid curator

The historical journal-curation cycle remains available only as `lucid.curate` during migration. It must not be expanded into user modeling or identity mutation. Its useful operational mechanics
(cursoring, re-emergence, stale-signal handling, duplicate avoidance and
recovery) may be migrated into their owning systems over time.
