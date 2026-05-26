# Lucid Platform Notes

## Iteration Budget

The 40-journal-per-run cap and incremental cursor keep turn count well within the default iteration budget. Each filing cycle (read journal → check duplicate → file → advance cursor) resets the activity-based timeout in Hermes v0.8+, so long runs complete naturally without inactivity timeouts.

## Cron Configuration

Cron runs use isolated session, light context. Operators with high journal volume (many active skills) may benefit from raising `max_turns` to 150 in their agent config.

## Heartbeat

No heartbeat entry. Lucid needs one substantial batch run per day, not lightweight polling.

## Mid-Run Termination Safety

If a session terminates mid-run, no filed work is lost. The cursor advances after each successful filing. The next run picks up from the first unprocessed journal.
