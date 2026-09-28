# Cron Execution — Lucid Dreaming

Lucid has two canonical Dreaming cron jobs and one optional legacy curator job.

## User Dreaming

Run as a script job:

```bash
python3 /root/.hermes/profiles/indigo/skills/ocas-lucid/scripts/lucid_user_dream.py --json
```

Recommended schedule: `10 3 * * *` local.

The script:

1. loads Chronicle through `ChronicleCore.get()`;
2. resolves exactly one human relationship subject, or requires `--principal`;
3. resumes from the prior User Dreaming Chronicle sequence watermark;
4. reads Chronicle's descriptive interaction-pattern surface;
5. rejects missing, non-human, or cross-principal source events;
6. stages a relationship-domain candidate;
7. gates it;
8. writes accepted derivations through Chronicle's atomic capture/reducer path;
9. reads the resulting Chronicle event back and verifies it;
10. promotes Lucid state only after that durable verification.

No direct Chronicle SQLite mutation is permitted.

## Self Dreaming

Run as a script job:

```bash
python3 /root/.hermes/profiles/indigo/skills/ocas-lucid/scripts/lucid_self_dream.py --json
```

Recommended schedule: `15 0 * * *` local, after Autobio daily observation and
before the daily micro-distillation.

The script resolves the agent principal, reads the latest Autobio observation,
stages it in the `self` namespace, applies the self gate, and records the run.
It never writes SOUL.

## Principal ambiguity

Both jobs fail closed.

- User Dreaming proceeds without `--principal` only when Chronicle contains
  exactly one principal of type `user`.
- Self Dreaming proceeds without `--principal` only when an active/unique
  agent principal can be resolved.

Do not guess a principal from profile names, filenames, or prose.

## State paths

```
<hermes-home>/commons/data/dreaming/
  profiles/<profile_id>/
    principals/<subject_principal_id>/
      relationship.json
      self.json
```

The store records profile/principal metadata and rejects mismatched reads or
writes.

## Legacy curator

The former `lucid.dream` journal scanner is now `lucid.curate`:

```bash
python3 /root/.hermes/profiles/indigo/skills/ocas-lucid/scripts/lucid_curate.py --json
```

Keep this cron only while another component still consumes the curated journal
artifacts. Its implementation is `scripts/lucid_dream_template.py`.

The curator:

- may read OCAS journals;
- may write only its own curator data/journals;
- must not directly access retired MemPalace/Elephas storage;
- must not manufacture user-principal evidence;
- must not be used as a substitute for User Dreaming.

## Cron safety

- Prefer `no_agent` script jobs for User/Self Dreaming: the paths are
  deterministic and do not require an LLM merely to orchestrate them.
- Never overlap self-Dreaming with Autobio observation production.
- A successful process exit is not enough for User Dreaming; promotion requires
  Chronicle read-back verification.
- Re-running a job without new evidence must not increase confidence.
