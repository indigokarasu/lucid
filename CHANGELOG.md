## [3.2.0] - 2026-09-26

### Fixed
- **`lucid_dream_template.py --help` executed a full 200-journal dream cycle.** The script had no argument parsing whatsoever, so any flag — including `--help` — fell through to `main()` and ran the cycle, advancing the cursor and writing journals. Added argparse with `--help`, `--dry-run`, `--batch-size`, `--json`, and meaningful exit codes (2 = bad usage / missing `config.json`).
- **`--dry-run` was not read-only.** The first implementation guarded evidence, the dream journal, and `config.json` but still appended to `decisions.jsonl`, `ingestion_log.jsonl`, and `recirculation_queue.jsonl`, and still called the MemPalace KG writer. All writes are now guarded; verified byte-for-byte via md5 across all five state files.
- **`update.sh` silently destroyed uncommitted work.** It ran `git reset --hard` + `git clean -fd` + `git pull` with every error sent to `/dev/null`, so a failed pull or a dirty worktree produced no output and no error. Now: `--help`, `--dry-run`, `--force`; refuses on a dirty worktree (exit 3) or diverged commits (exit 4); uses `git pull --ff-only`; surfaces errors.
- **Incorrect `re_evaluations` guidance.** SKILL.md claimed a `None >= 3` comparison "returns `False` in Python and silently skips cleanup." In Python 3 that raises `TypeError`; the real hazard is an outer handler swallowing it. Corrected.

### Added
- `metadata.hermes.tags` / `category` and `triggers` frontmatter (D1).
- Dream cycle and initialization checklists; Error handling table with failure/symptom/handling pairs (D5, D7).
- "Why" rationale for the rigid safety gates and the non-obvious sorting/degraded-mode rules (D6).
- `references/cron-execution-detail.md` — extracted the priority table, scan exceptions, two-pass workflow, and degraded-mode tree out of SKILL.md (D3/D4/D8). SKILL.md 265 → 333 lines with far less duplication.
- Bundled-scripts table documenting flags and exit codes (D4/D8/D9).
- `tests/test_smoke.py` (15 tests) and a CI workflow locking the CLI contract: `--help` must exit 0 without executing a cycle, unknown flags exit 2, `--dry-run` is read-only, and importing the template has no side effects (D8).

### Changed
- SKILL.md reduced to 308 lines / ~3.5k tokens by extracting the scoring traps, boundaries and interfaces, recovery and scheduling, the full support file map, and the long error table into `references/`. All four keep a "When to read" pointer; the support file map is now itself a reference. The inline error table was reduced to the six highest-value rows with a pointer to `references/error-handling.md` for the rest.

## [3.1.0] - 2026-09-16

### Added
- **Schedule gap recovery** — morning gap detection re-processes missed 3am `lucid:dream` runs if the system was asleep; logs schedule_gap and batches with `lucid:update`.

## [2.0.2] - 2026-04-26

### Changed
- Version alignment: SKILL.md frontmatter, CHANGELOG.md, and GitHub release tag now in sync per spec-ocas-skill-publishing.md. No functional change in this release.

## [2.0.0] - 2026-04-13

### Changed
- Complete rewrite of the dream cycle architecture
- Replaced single-pass background loop with a deterministic four-phase pipeline: Orient, Gather, Classify, File
- Replaced `$AGENT_DATA_ROOT` paths with `{agent_root}/commons/` convention for platform portability
- Signal emission now uses journal signal payload field (standard OCAS pattern) instead of direct write to Elephas intake directory
- `references/classification.md` moved to `references/` directory

### Added
- Incremental cursor: ingestion log tracks last processed run_id per skill; mid-run termination loses no filed work
- Re-emergence detection: topics skipped 3+ times in subsequent journals are auto-promoted
- Two-pass stale handling: MemPalace entries require two consecutive contradictions before invalidation
- Change magnitude gates: >30% file rate warns; >50% halts and stages for operator review
- Hibernation protection: skip cycle entirely if no new journals for 7 consecutive days
- Relevance scoring model with additive signals and penalties (see `references/classification.md`)
- Wing/room assignment taxonomy for all OCAS skill domains
- `lucid:update` cron job (midnight daily self-update)
- `lucid.update` command and self-update procedure
- MemPalace declared as required MCP in frontmatter
- Standard `hermes:` and `openclaw:` frontmatter structure

### Removed
- `dream-loop.py`, `init-script.py`, `cron-command.sh` scripts (agent now reasons directly)
- `ocas-layer`, `ocas-visibility`, `ocas-skill-type`, `ocas-cron` custom frontmatter fields
- `compatibility:` non-standard frontmatter field (moved to `requires.mcp`)

## [1.0.0] - 2026-04-09

### Added
- Initial implementation: nightly dream loop reviewing session interactions for MemPalace/Chronicle ingestion
- Dual-phase process: Fresh Scan and Weak Signal Recirculation
- Background execution mode to avoid timeout on long-running analysis