# Support File Map

Every reference and script, with the condition under which to read it. Read
this when you are about to run a cycle and need to know which detail file
applies.

| File | When to read |
|------|-------------|
| `references/classification.md` | Before classifying any journal entry. Relevance scoring model, filing taxonomy, wing/room assignment rules, skip criteria. |
| `references/dream-cycle.md` | Before executing the dream cycle. Phase-by-phase procedure (Orient, Gather, Classify, File), cursor tracking, filing pitfalls. |
| `references/cron-execution.md` | Before running any dream cycle in cron context. Heredoc Python pattern, two-pass classification, degraded-mode decision tree. |
| `references/cron-execution-detail.md` | When writing or debugging a dream cycle invocation. Skill-priority table, skill-level scan exceptions, two-pass first-run workflow, cron environment constraints. |
| `references/safety-gates.md` | After classification, before filing. Change magnitude gates (>30% warning, >50% staging hold) and hibernation protection. |
| `references/re-emergence.md` | During post-file cleanup. Re-emergence detection (3+ threshold, auto-promotion) and two-pass stale handling. |
| `references/dream-journal.md` | When writing the dream journal. Full output schema (counts, events, Signal payload, skip path). |
| `references/okr.md` | During OKR evaluation. Targets for ingestion coverage, duplicate avoidance, recirculation, Signal precision, schedule adherence, data integrity. |
| `references/gotchas.md` | Before any dream cycle run. Journal discovery, KG triples, null fields, ingestion log formats, cursor resumption, recirculation queue. |
| `references/scoring-traps.md` | When a run files the wrong thing, files something twice, or files nothing across several consecutive runs. |
| `references/boundaries-and-interfaces.md` | When deciding which component should handle a task or when wiring a new consumer of Lucid output. Full read/write/query surface. |
| `references/recovery-and-scheduling.md` | When a run was missed, when the evidence log looks wrong, or during OKR evaluation. Recovery contract, cron job table, schedule-gap recovery. |
| `references/bridge-health-check.md` | When diagnosing remaining LadybugDB-based domain stores such as Weave. Not a Chronicle or Lucid dependency. |
| `references/platform-notes.md` | When a tool is unexpectedly missing in a cron run (`execute_code`, `memory`), or when sizing `max_turns` for a large backlog. |
| `references/interactive-menu.md` | When Lucid is invoked interactively and a two-level menu must be presented. |
| `scripts/lucid_dream_template.py` | Before running a dream cycle by hand, and whenever you need to preview a batch instead of committing it. Copy to `/tmp/`; `--dry-run` previews, `--batch-size N` overrides the 200 cap, `--json` emits a machine-readable summary. |
| `scripts/update.sh` | When self-updating the skill. `--dry-run` previews; the default run **refuses** (exit 3) on a dirty worktree; `--force` opts into a destructive reset. |

## Known-missing references

`references/dream-cycle.md`, `references/re-emergence.md`,
`references/safety-gates.md`, and `references/dream-journal.md` may not exist on
disk in some checkouts. When a listed file is absent, fall back to the
procedural instructions in the SKILL.md body and do not block the run.
