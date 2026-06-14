# Classification Reference

Relevance scoring model, filing taxonomy, wing/room assignment rules, and skip criteria for Lucid's dream cycle.

## Scoring Rubric

Each journal is scored by examining its **narrative text fields** (summary, description, reasoning_summary, findings, analysis, report) — NOT payload dictionary keys.

| Signal | Points | Condition |
|--------|--------|-----------|
| `correction_or_lesson` | +4 | Narrative contains lesson/learning language: "learned", "correction", "mistake", "improvement", "should have", "could have", "better approach", "next time", "avoid", "fix", "resolved", "solution", "workaround" |
| `decision_keywords` | +3 | Narrative contains decision language: "decided", "decision", "chose", "selected", "determined", "conclusion", "recommend", "adopt", "approved", "rejected", "prefer", "opt for", "go with" |
| `entity_density` | +2 | Journal contains structured entity data: `entities_observed`, `persons_upserted`, `relationships_discovered`, `identities_merged` fields present |
| `blocker_context` | +2 | Narrative describes blockers/issues with context: "blocked", "blocker", "error", "failed", "failure", "issue", "problem", "unavailable", "exhaustion", "limit", "rate limit", "429", "timeout", "crash" AND has meaningful narrative (>200 chars) |
| `cross_skill` | +2 | Narrative references cross-skill coordination: "cross-skill", "integration", "coordinated", "multiple skill", "skill cooperation", "inter-skill", "between skills" |
| `adaptations` | +2 | Narrative describes local adaptations/customizations: "local_adaptation", "adapted", "customized", "modified", "preserved", "conflict_resolution", "merge conflict" |
| `user_directed` | +3 | Journal type is "Action" or "Interaction" (user-initiated) |
| `artifacts` | +1 | Journal has substantial narrative content (>500 chars) with meaningful text |

## Filing Thresholds

| Score | Filing Action |
|-------|---------------|
| ≥ 5 | **file** — write to MemPalace drawers + KG |
| 3–4 | **recirculate** — add to recirculation queue for re-evaluation |
| ≤ 2 | **skip** — no filing, cursor advances only |

## Pure Metrics Skip (Early Exit)

Journals with **no narrative** AND **text length < 300 chars** receive `-3` (`pure_metrics`) and are skipped immediately. This catches routine heartbeat/light-scan journals.

## Wing Assignment

Maps skill → MemPalace wing (falls back to `root/<room>` if custom wings unavailable):

| Skill | Wing | Room (topic slug) |
|-------|------|-------------------|
| ocas-custodian, custodian | system | operations |
| ocas-mentor, ocas-finch, ocas-forge, ocas-praxis | evolution | evolution |
| ocas-scout, ocas-rally, ocas-sift, ocas-reach | research | research |
| ocas-dispatch, ocas-haiku, ocas-weave, ocas-spot, ocas-vesper | operations | operations |
| ocas-sands, ocas-voyage, ocas-look, ocas-taste | preferences | preferences |
| ocas-elephas, ocas-corvus, corvus | knowledge | knowledge |
| ocas-bower, ocas-expansion, ocas-bones | operations | operations |

## Skip Criteria (Auto-Skip Regardless of Score)

- Pure metrics/heartbeat journals (early exit above)
- Journal type "Observation" with no entities, no lessons, no decisions, no blockers
- Self-update journals with only version bump (no adaptations preserved)
- Routine sync journals (Spotify sync, calendar scan) with only success/failure status

## Classification Algorithm (Two-Pass)

### Pass 1: Narrative Extraction
```python
def extract_narrative(journal):
    # Check narrative fields only — NOT payload keys
    narrative_fields = ["summary", "description", "reasoning_summary", 
                        "findings", "analysis", "report", "notes", "text", "content"]
    parts = []
    for field in narrative_fields:
        val = journal.get(field)
        if isinstance(val, str) and len(val) > 10:
            parts.append(val)
    return " ".join(parts)[:3000]
```

### Pass 2: Signal Detection
Apply keyword checks to **extracted narrative text only** (lowercased). Never count payload key names like `lessons_extracted` as signal triggers.

## Edge Cases Handled

- **Elephas deep consolidation journals**: Have `identities_merged`, `relates_created` → entity_density(+2). Often pure metrics otherwise → skip unless lessons/decisions present.
- **Vesper briefings**: Have decisions sections + entity data → typically score 8+ (file).
- **Scout/Sift expansion journals**: Often have entity data + blocker context (API limits) → score 5 (file).
- **Weave upsert journals**: Entity data only → score 3 (recirculate) unless cross-skill issue present.
- **Haiku content reviews**: Blocker context only → score 3 (recirculate).
- **Dispatch triage/draft journals**: Routine operational → skip (score 0 or -3).

## Re-circulation Queue

Entries added with:
```json
{
  "skill": "...",
  "run_id": "...",
  "journal": "...",
  "added_at": "...",
  "score": 3,
  "reason": "Score in recirculation range (3-4): signal1(+N), signal2(+M)"
}
```

`re_evaluations` field defaults to 0. Use `e.get('re_evaluations') or 0` — older entries may have `null`.