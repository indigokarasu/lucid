# Lucid Dreaming Scheduling

Lucid owns the Dreaming schedules. The two domains run separately even though
they share one repository and kernel.

## Required jobs

| Job | Schedule | Purpose |
|---|---|---|
| `lucid:user-dream` | daily 02:20 local | Chronicle -> user-principal consolidation |
| `lucid:self-dream` | daily 00:05 local | latest Autobio observation -> self staging |
| `lucid:curate` | optional during legacy migration | old journal curator |

Self Dreaming must run after Autobio's daily observation and before the daily
SOUL micro-distillation if the distillation is expected to consume same-day
self insight. Deployment schedules therefore need to leave enough wall-clock
space for the observation job to finish; do not overlap these jobs merely to
keep historical clock times.

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
