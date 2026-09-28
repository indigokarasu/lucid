# Skill Boundaries and Interfaces

Lucid is the canonical OCAS Dreaming implementation. It owns shared Dreaming
mechanics and two isolated execution domains; it does not own the canonical
stores those domains feed.

## Ownership

Lucid owns:

- User Dreaming orchestration;
- self-Dreaming orchestration;
- owner/subject/domain-isolated candidate state;
- gate-before-promotion;
- Dreaming run/watermark state;
- Chronicle and Autobio adapters;
- the optional legacy curator compatibility path.

Lucid does not own:

| Concern | Owner |
|---|---|
| Canonical interaction/world evidence | Chronicle |
| Durable user-domain memory, contradiction, correction, forgetting | Chronicle |
| Descriptive user interaction-pattern mining | Chronicle |
| Agent autobiography / SOUL | Autobio/SOUL |
| Agent/system behavioral adaptation | Finch/Praxis |
| Skill evaluation | Mentor/Fellow |
| Skill implementation | Forge |
| Social graph | Weave |

## Chronicle principal vs human subject

Chronicle's current capture model owns conversation events under the active
agent principal. Human authorship is a separate speaker-attribution property.

For User Dreaming:

- `owner_principal_id` identifies the Chronicle agent owner;
- `user_subject_id` identifies the human relationship subject;
- durable accepted memory is written under the owner principal with
  `domain="user"`;
- Lucid state is nested under both owner and subject.

A human is never fabricated as a Chronicle principal merely to make the
Dreaming model look symmetrical.

## User Dreaming boundary

Every durable User Dreaming result:

- derives only from human-attributed Chronicle events;
- preserves Chronicle source event ids;
- is scoped to the selected Chronicle owner and human subject;
- is committed through Chronicle's atomic append/reducer path;
- is read back and verified before Lucid promotion;
- remains user-domain memory, never agent identity.

If recent owned evidence contains multiple explicit human authors and no human
subject was selected, Lucid stops.

## Self Dreaming boundary

Self Dreaming consumes Autobio observations and stages only the `self` domain.

For self Dreaming the Chronicle owner and subject are the same agent principal.
A promoted self candidate means "eligible evidence for Autobio". It does not
edit character files, principles, or SOUL.

## State boundary

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<owner_principal_id>/
      subjects/<subject_id>/
        relationship.json
        self.json
```

The store records and validates profile, owner principal, subject, and domain.
Cross-owner, cross-subject, and cross-domain access is rejected.

## Legacy curator boundary

`lucid.curate` may continue to scan journals and write Lucid-owned curated
artifacts during migration. It is not User Dreaming or self-Dreaming.

It must not write retired MemPalace/Elephas stores, infer a human subject from
unattributed multi-user evidence, write SOUL, or turn its own output into fresh
independent evidence for User Dreaming.

## Failure semantics

- Chronicle evidence missing or wrong owner: reject.
- Explicit human author mismatches selected subject: reject.
- Multiple explicit human authors with no selected subject: fail closed.
- Chronicle durable write/read-back failure: hold; do not promote.
- Missing Autobio observation: fail self-Dreaming; do not fabricate.
- Legacy curator failure: does not alter User/Self Dreaming state.
