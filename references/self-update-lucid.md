# Self-Update Procedure for Lucid

## Purpose
Allow Lucid to update its own skill repository (indigokarasu/lucid) and reload configuration without manual intervention.

## When to Trigger
- Scheduled: Weekly check (config: `self_update_check_days`, default 7)
- Manual: `lucid.dream --self-update`
- Auto: When dream cycle detects config schema version mismatch

## Procedure

### 1. Pre-Update Checks
- [ ] Verify git status clean in `~/.hermes/profiles/indigo/skills/indigo/ocas-lucid/` (or skill repo root)
- [ ] Fetch origin: `git fetch origin main`
- [ ] Compare local HEAD vs origin/main
- [ ] If behind: proceed. If ahead or diverged: log warning, skip auto-update (requires manual resolution)

### 2. Update Execution
```bash
cd ~/.hermes/profiles/indigo/skills/indigo/ocas-lucid/
git pull origin main --ff-only
# If ff-only fails: abort, log divergence to evidence.jsonl
```

### 3. Post-Update Validation
- [ ] Verify SKILL.md frontmatter `version` incremented
- [ ] Validate YAML syntax: `python -c "import yaml; yaml.safe_load(open('SKILL.md'))"`
- [ ] Run script syntax checks: `python3 -m py_compile scripts/*.py` (if scripts exist)
- [ ] Verify all references/ files present (cross-check Support File Map)
- [ ] Test config.json schema compatibility (new fields have defaults)

### 4. Reload & Resume
- [ ] Hermes hot-reloads skill on next invocation (no restart needed for SKILL.md changes)
- [ ] If scripts changed: next cron run picks up new versions automatically
- [ ] Write self-update event to dream journal signals:
  ```json
  {
    "type": "self_update",
    "previous_version": "3.0.1",
    "new_version": "3.0.2",
    "commit": "abc1234",
    "status": "success"
  }
  ```

### 5. Rollback (If Validation Fails)
- `git reset --hard HEAD@{1}`
- Log failure to evidence.jsonl with error details
- Continue running on previous version
- Alert via dream journal signal `type: "self_update_failed"`

## Configuration

```json
{
  "self_update": {
    "enabled": true,
    "check_days": 7,
    "auto_apply": true,
    "require_ff_only": true,
    "validate_before_apply": true
  }
}
```

## Safety Gates
- **FF-only pull**: Prevents merge commits and history rewriting
- **Clean working tree required**: No local modifications lost
- **Schema validation**: New config fields must have defaults; breaking changes blocked
- **Version bump required**: Update must increment frontmatter version
- **Rollback on failure**: Atomic — either fully applied or fully reverted