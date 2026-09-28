# Recovery, Scheduling, and OKRs

Operational contracts for Lucid's canonical Dreaming pipelines and the legacy
curator compatibility path.

## User Dreaming recovery

User Dreaming records every run in the target user principal's relationship
state:

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<user-principal>/
      relationship.json
```

Each run records a Chronicle sequence watermark. The next run resumes from the
highest recorded `last_seq`. Re-running without new Chronicle evidence does
not increase confidence.

If a Chronicle durable write fails or cannot be read back and verified, the
candidate remains `hold`; it is not promoted. The command returns non-zero
when a write raised an error.

## Self Dreaming recovery

Self Dreaming records each source observation path and run under the agent
principal's `self.json`. Running the same observation again produces the same
candidate id; promotion remains self-domain staging only.

A missing Autobio observation is a run failure. It must not be replaced with an
invented or user-domain observation.

## Required background jobs

| Job | Schedule | Command |
|---|---|---|
| `lucid:user-dream` | daily 03:10 local | `python3 scripts/lucid_user_dream.py --json` |
| `lucid:self-dream` | daily 00:15 local | `python3 scripts/lucid_self_dream.py --json` |

The deployment should schedule Autobio's daily micro-distillation after
`lucid:self-dream` if same-day self insight is expected to participate in the
distillation.

## Legacy curator

The old journal curator remains optional as `lucid:curate`.

Its recovery contract is unchanged:

- every curator cycle appends an evidence record under
  `commons/data/ocas-lucid/evidence.jsonl`;
- ingestion/cursor state resumes from prior processed paths;
- a missed curator cycle can be run once on the next wake;
- Chronicle unavailability does not authorize direct database or retired
  MemPalace writes.

The legacy curator is not a substitute for either Dreaming job.

## OKR evaluation

Dreaming OKRs should separately measure:

- user-principal provenance validity;
- cross-principal rejection;
- durable-write verification;
- candidate hold/block/promote rates;
- watermark continuity;
- self/user domain isolation;
- Autobio consumption of promoted self evidence.

Legacy curator OKRs remain documented in `okr.md` until that compatibility
surface is removed.
