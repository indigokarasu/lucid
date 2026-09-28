# Recovery, Scheduling, and OKRs

Operational contracts that apply to every run rather than to one phase.
Read this when a run was missed, when the evidence log looks wrong, or during
OKR evaluation.

## Recovery behavior

Implements the recovery contract from `spec-ocas-recovery.md`.

- **Evidence** — every dream cycle appends a record to
  `{agent_root}/commons/data/ocas-lucid/evidence.jsonl`, including skip and
  hibernation runs. `not_activity_reason` is mandatory when no side effects
  occur.
- **Gap detection** — on every wake, check the evidence log. If the gap exceeds
  24h for a dream cycle, log `gap_detected` and run a catch-up pass (capped at
  40 journals).
- **Downstream-memory degradation** — Chronicle ingestion unavailability does not block Lucid classification or curated journal writes. Retry ingestion downstream. When journal sources are
  missing, continue with the available sources.
- **Log compaction** — ingestion logs older than 30 days (no-op) or 90 days
  (error/gap) are compacted. Last 7 days are retained.

## Background jobs

| Job name | Mechanism | Schedule | Command |
|----------|-----------|----------|---------|
| `lucid:dream` | cron | `0 3 * * *` (3am local) | `lucid.dream` |
| `lucid:update` | cron | `0 0 * * *` (midnight daily) | `lucid.update` |

### Schedule gap recovery

If the system was asleep at the 3am `lucid:dream` run, the morning gap
detector re-processes the missed run. On the next wake / morning invocation,
check whether a dream cycle ran for the expected date (scan the run journal
directory for the target `YYYY-MM-DD`); if absent, run `lucid.dream` once to
catch up. Log the gap (`schedule_gap=missed→recovered`) and optionally batch
with `lucid:update` so the missed nightly curation still lands the same day.

## Re-emergence detection and stale handling

See `re-emergence.md` for the full algorithm: a 3+ journal threshold with
auto-promotion, and two-pass stale handling (mark on the first contradiction,
invalidate on second confirmation).

## OKR evaluation

Universal OKRs per `spec-ocas-journal.md`, plus skill-specific targets. See
`okr.md` for the full table: ingestion coverage, duplicate avoidance,
recirculation, Signal precision, schedule adherence, data integrity.
