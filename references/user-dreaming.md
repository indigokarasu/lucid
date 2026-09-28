# User Dreaming

User Dreaming is Lucid's user-principal offline consolidation pipeline.

It consumes Chronicle's descriptive interaction-pattern evidence, stages a
relationship-domain candidate, applies the deterministic gate, commits accepted
results through Chronicle's atomic event/reducer path, verifies the durable
write, and only then promotes Lucid's candidate state.

## Invariants

- Subject is the user principal.
- Chronicle remains canonical durable memory.
- Lucid never writes Chronicle SQLite directly.
- Every accepted relationship derivation points to human-attributed Chronicle
  event ids.
- Evidence must belong to the target user principal.
- A failed or unverifiable Chronicle write leaves the candidate held.
- Lucid's own previous output is not independent evidence.
- Relationship state never becomes self/SOUL state.

## Command

```bash
python3 scripts/lucid_user_dream.py \
  --hermes-home /root/.hermes \
  --profile indigo \
  --principal <user-principal> \
  --json
```

If `--principal` is omitted, Lucid proceeds only when Chronicle contains
exactly one principal of type `user`. Zero or multiple users fail closed.

The runner resumes from the highest `last_seq` recorded by prior successful
User Dreaming runs unless `--since-seq` is supplied.

## Gate

The initial deterministic gate requires:

- authoritative Chronicle event references;
- support from at least two matching turns;
- confidence >= 0.72.

This is deliberately conservative. The gate can later incorporate the full
recovered Dreaming verifier/repair stack without changing the ownership model.

## Durable write

Accepted relationship derivations are Chronicle notes with:

- owner = target user principal;
- domain = `user`;
- note type = `user_dreaming`;
- source type = `user_dreaming`;
- event parents = all supporting Chronicle event ids.

Promotion in Lucid happens only after the resulting Chronicle event is read
back and verified.

## State

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<user-principal>/
      relationship.json
```

This state is process/audit state, not canonical user memory.
