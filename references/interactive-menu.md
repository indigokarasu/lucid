# Interactive Menu

When Lucid is invoked interactively, present the subject-specific Dreaming
operations first. Do not use the ambiguous historical `dream` label.

```python
result = clarify(
    question="What would you like Lucid to do?",
    choices=[
        "user-dream — Consolidate user/relationship evidence from Chronicle",
        "self-dream — Stage agent self-reflection from Autobio",
        "status — Show Dreaming state and recent run status",
        "curate — Run the legacy journal curator",
        "init — Initialize Dreaming state / schedules",
        "update — Pull latest from GitHub",
    ]
)
```

## Routing

- `user-dream` → `lucid.user-dream`
- `self-dream` → `lucid.self-dream`
- `curate` → `lucid.curate`
- `status` → show both principal/domain states plus legacy curator status

The menu must never collapse user and self Dreaming into one stateful run.
A user may request both; execute them sequentially with independent principals
and stores.

### Response parsing

Match the user's response against the full choice string. If the response
doesn't match any known choice, match key prefixes case-insensitively.
Re-present the menu on no match.

### Platform adaptation

On CLI, choices are navigable with arrow keys. On messaging platforms, choices
render as a numbered list.
