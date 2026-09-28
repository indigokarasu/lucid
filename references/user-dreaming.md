# User Dreaming

User Dreaming is Lucid's offline consolidation pipeline for one human
relationship subject.

## Chronicle ownership model

Chronicle currently stores captured interaction memory under the active
**agent principal**. Human authorship is represented by speaker attribution,
and user-memory semantics are represented by `domain="user"`.

Lucid therefore keeps two identifiers separate:

- **owner principal** — the Chronicle agent principal that owns the memory;
- **user subject** — the human whose relationship/user model is being
  consolidated.

These must never be collapsed into one principal id.

## Pipeline

1. Resolve the Chronicle owner agent principal.
2. Resolve the human subject from explicit host author metadata; if none exists
   in a single-user deployment, use the scoped fallback `primary_user`.
3. Recompute Chronicle descriptive interaction patterns over the bounded
   historical window.
4. Keep only human-authored source events owned by the selected agent principal
   and belonging to the selected human subject.
5. Require new evidence beyond the prior run watermark.
6. Stage a relationship-domain candidate.
7. Apply the deterministic gate.
8. Commit accepted results through Chronicle's atomic event/reducer path with
   `domain="user"`.
9. Read the Chronicle event back and verify the durable write.
10. Promote Lucid state only after verification.
11. Record the Chronicle sequence watermark even when no candidate promoted.

## Invariants

- Chronicle remains canonical durable memory.
- Lucid never writes Chronicle SQLite directly.
- Every accepted relationship derivation points to human-attributed Chronicle
  event ids.
- Evidence must be owned by the selected Chronicle agent principal.
- Explicit human-author evidence must match the selected user subject.
- In a multi-author scope, `--user-subject` is mandatory.
- A failed or unverifiable Chronicle write leaves the candidate held.
- A held pattern may accumulate later evidence; the watermark must not make it
  permanently unreachable.
- Lucid's own prior output is not independent evidence.
- Relationship state never becomes self/SOUL state.

## Command

```bash
python3 scripts/lucid_user_dream.py \
  --hermes-home /root/.hermes/profiles/indigo \
  --profile indigo \
  --principal <chronicle-agent-principal> \
  --user-subject <human-author-id> \
  --json
```

`--principal` means the Chronicle **owner agent principal**, not the user.

If `--principal` is omitted, Lucid uses Chronicle's active agent principal or
requires exactly one agent principal. If `--user-subject` is omitted, Lucid
accepts exactly one explicit human author in recent owned evidence; if author
metadata is absent, it uses `primary_user`. Multiple explicit authors fail
closed.

## Gate

The initial deterministic gate requires:

- authoritative Chronicle event references;
- support from at least two matching turns;
- confidence >= 0.72.

Patterns are recomputed over bounded history on each run so a previously-held
candidate can gain support from later evidence. Only patterns whose newest
eligible evidence is newer than the previous watermark are reconsidered.

## Durable write

Accepted relationship derivations are Chronicle notes with:

- owner = Chronicle agent owner principal;
- domain = `user`;
- note type = `user_dreaming`;
- subject = `relationship:<user_subject_id>`;
- source type = `user_dreaming`;
- event parents = all supporting Chronicle event ids.

## State

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<chronicle-agent-principal>/
      subjects/<user_subject_id>/
        relationship.json
```

This is Dreaming process/audit state, not canonical user memory.
