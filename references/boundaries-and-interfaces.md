# Skill Boundaries and Interfaces

Lucid is the canonical OCAS Dreaming implementation. It owns shared Dreaming
mechanics and two isolated execution domains; it does not own the canonical
stores those domains feed.

## Ownership

Lucid owns:

- User Dreaming orchestration;
- self-Dreaming orchestration;
- principal/domain-isolated candidate state;
- gate-before-promotion;
- Dreaming run/watermark state;
- Chronicle and Autobio adapters;
- the optional legacy curator compatibility path.

Lucid does not own:

| Concern | Owner |
|---|---|
| Canonical interaction/world evidence | Chronicle |
| Durable user memory, contradiction, correction, forgetting | Chronicle |
| Descriptive user interaction-pattern mining | Chronicle |
| Agent autobiography / SOUL | Autobio/SOUL |
| Agent/system behavioral adaptation | Finch/Praxis |
| Skill evaluation | Mentor/Fellow |
| Skill implementation | Forge |
| Social graph | Weave |

## User Dreaming boundary

User Dreaming consumes only user-grounded Chronicle evidence. Every durable
result:

- targets an explicit user principal;
- preserves Chronicle source event ids;
- is committed through Chronicle's atomic append/reducer path;
- is read back and verified before Lucid promotion;
- remains user memory, never agent identity.

Lucid never writes Chronicle SQLite directly.

If Chronicle has multiple user principals and none is explicitly selected,
Lucid stops.

## Self Dreaming boundary

Self Dreaming consumes Autobio observations and stages only the `self` domain.

A promoted self candidate means "eligible evidence for Autobio". It does not
edit character files, principles, or SOUL. Autobio remains the identity
authority.

User/relationship candidates are forbidden from self promotion.

## State boundary

Dreaming state is process/audit state:

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<subject_principal_id>/
      relationship.json
      self.json
```

The store records and validates profile/principal identity on every load/save.
Cross-principal and cross-domain access is rejected.

## Legacy curator boundary

`lucid.curate` may continue to scan journals and write Lucid-owned curated
artifacts during migration. It is not User Dreaming or self-Dreaming.

It must not:

- write retired MemPalace/Elephas stores;
- infer a user principal from an unattributed journal;
- write SOUL;
- turn curator output into fresh independent evidence for User Dreaming.

## Failure semantics

- Chronicle evidence missing/cross-principal: reject candidate.
- Chronicle durable write failure: hold candidate; do not promote.
- Chronicle read-back verification failure: hold candidate.
- Missing Autobio observation: fail self-Dreaming; do not fabricate.
- Principal ambiguity: fail closed.
- Legacy curator failure: does not alter User/Self Dreaming state.
