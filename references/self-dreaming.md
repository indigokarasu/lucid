# Self Dreaming

Self Dreaming is Lucid's agent-principal reflection staging pipeline.

It consumes Autobio observations and promotes sufficiently substantive,
grounded observations into Lucid's `self` domain. A Lucid self promotion means
only "eligible evidence for Autobio". It never edits character files or SOUL.

## Invariants

- Subject is the active agent principal.
- Autobio/SOUL remains the identity authority.
- Relationship/user candidates cannot enter self state.
- Self candidates cannot enter user memory.
- The source observation path is retained as evidence.
- SOUL changes still require Autobio's own distillation/evolution gate.

## Command

```bash
python3 scripts/lucid_self_dream.py \
  --hermes-home /root/.hermes \
  --profile indigo \
  --principal <agent-principal> \
  --observations-dir /indigokarasu/SOUL/autobio/observations \
  --json
```

If `--observation` is omitted, the lexically latest Markdown observation is
used.

## State

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<agent-principal>/
      self.json
```

Autobio may read the promoted set as another evidence source during
distillation. Lucid does not write SOUL.
