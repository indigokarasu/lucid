# Scoring Traps

Non-obvious failure modes in classification and filing. Each has caused real
misclassification or duplicate writes in production; check here before
debugging a "filed the wrong thing" or "filed twice" report.

## Check the ledger before re-filing

Cursor rollbacks and interrupted runs can leave a source file still past the
cursor after it was already filed. Before writing a curated entry, grep
`decisions.jsonl` for the source path; if it already carries a `file` decision,
record `skip` with an `already_filed` note instead of writing a duplicate.

**Why**: the ingestion log is the authoritative processed-set, but a cursor
rollback can make the log and the cursor disagree. The ledger check is the only
cheap way to notice.

**Both the log lookup AND the ledger lookup must normalize paths.** A raw
substring grep is how this check silently passes: the log stores the symlink
spelling of the path while the discovered path is the resolved real one, so the
grep finds nothing and the duplicate is written anyway. Route every comparison
through `normalize()` and compare sets, not substrings — see the commons-symlink
entry in `references/gotchas.md`.

## Run id and folder come from the wall clock

Generate `run_id` as `lucid-<UTC now>` at write time and place the journal in
the folder for the run_id's UTC date. Never reuse a scheduled slot time —
actual fire times can differ (manual/off-schedule claims), and slot-derived
ids have disagreed with true run times before.

**Why**: a run claimed for 03:00 that actually fired at 04:12 would otherwise
be filed under the previous day's folder, breaking the per-day OKR view.

## Payload keys vs. narrative content

The `correction_or_lesson(+4)` signal must ONLY fire on narrative text fields
(`summary`, `description`, `reasoning_summary`). Do NOT count payload
dictionary **key names** (like `lessons_extracted`) as content — this causes
routine operational journals to score 6+ and get filed as noise. Apply keyword
checks to the extracted narrative text only, not to the full serialized JSON.

## Narrative extraction must handle nested structures

Top-level-only extraction misses ~80% of vesper content
(`decision.reasoning_summary`, `decision.payload.entities_observed`,
`run_identity.journal_type`) and ~60% of custodian findings
(`findings[].diagnosis`). `references/classification.md` carries the correct
multi-path extraction. **Always use the updated extraction, not the simplified
top-level version.**

## Principal eligibility is not classification confidence

A high relevance score does not imply that a journal is eligible for durable
personal memory. A curated artifact may be valuable evidence while carrying no
explicit principal. In that case write the curated artifact with
`memory_candidate: null`.

Never infer the user principal from skill name, file location, or narrative
content. The source journal must carry explicit principal ownership/provenance.

## Recirculation queue `re_evaluations` field

`re_evaluations` can be `null` (not 0) in older queue entries. Always use
`e.get('re_evaluations') or 0` when comparing. A bare `>= 3` against `None`
raises `TypeError` in Python 3 (it is not a quiet `False`), and the exception
can be swallowed by an outer handler so cleanup silently stops running.

## When interesting journals are buried under scan backlog

If the cursor is deep into a scan-heavy region (e.g., 2000+ unprocessed, mostly
mentor light scans), the standard 40-journal batch will process zero
interesting journals. **Mitigation**: run a targeted pass that collects
unprocessed journals only from high-signal skills (vesper, praxis, taste,
custodian, dispatch) and processes those first. This ensures the cursor
advances through scans *and* interesting signals get filed in the same session.
See `references/classification.md` Pass 1 for the narrative extraction
improvements needed to correctly score these journals.

## Reference file resilience

`references/dream-cycle.md`, `references/re-emergence.md`,
`references/safety-gates.md`, and `references/dream-journal.md` may not exist
on disk even though the Support File Map references them. When a reference file
is missing, fall back to the procedural instructions in the SKILL.md body
itself. Do not block the run.
