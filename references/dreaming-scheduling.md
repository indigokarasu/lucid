# Lucid Dreaming Scheduling

Lucid owns the Dreaming schedules. The two domains run separately even though
they share one repository and kernel.

## Required jobs

| Job | Schedule | Purpose |
|---|---|---|
| `lucid:user-dream` | daily 02:20 local | Chronicle -> user-principal consolidation |
| `lucid:self-dream` | daily 00:05 local | latest Autobio observation -> self staging |
| `lucid:curate` | optional during legacy migration | old journal curator |

Self Dreaming runs at 00:05 local, after the late-evening Autobio observation
window. It is idempotent by source path: if no newer observation exists, the run
records a no-op rather than re-promoting the same observation. Autobio/SOUL
remains responsible for when promoted self evidence is consumed by its own
distillation cycle.

User Dreaming is independent of the legacy curator and should run after the
previous day's normal Chronicle capture has settled.

## Recovery

Each Dreaming run writes a run record into its principal/domain state. User
Dreaming stores its Chronicle sequence watermark and resumes from that
watermark. Re-running with no new matching evidence does not increase
confidence by itself.

A failed Chronicle durable write leaves the User Dreaming candidate held and
returns a non-zero command status when the runner recorded an error.

## Legacy curator

The old `lucid:dream` journal-curation meaning is retired. Use:

```bash
python3 scripts/lucid_curate.py
```

Only keep the curator cron while another consumer still depends on its curated
journal artifacts. Do not use curator output as fresh evidence for User
Dreaming.


## Registration and migration

Run:

~~~bash
python3 scripts/lucid_init.py --json
~~~

The command is idempotent. It uses Hermes cron management rather than editing
jobs.json directly.

It guarantees one canonical job for each required Dreaming domain. If the
historical job name lucid:dream exists, it is edited in place to lucid:curate
when legacy curation is retained, preserving the existing job id/history.
Duplicate canonical jobs are removed.

To retire the old curator completely:

~~~bash
python3 scripts/lucid_init.py --no-legacy-curator --json
~~~

Use scripts/lucid_status.py to inspect the currently registered Lucid jobs and
the latest principal/domain run records.
