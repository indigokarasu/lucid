# ⚙️ Lucid

  <img src="./assets/readme/hero.jpg" width="100%" alt="Lucid">

Canonical OCAS Dreaming implementation. Runs principal-scoped User Dreaming and agent self-Dreaming with a shared, domain-isolated kernel.

**Skill name:** `ocas-lucid`
**Version:** 4.1.0
**Type:** Dreaming / offline consolidation
**Layer:** Memory + Self Evolution
**Author:** Indigo Karasu

---

## 📖 Overview

Lucid is the canonical home of OCAS Dreaming. One repository provides a shared
Dreaming kernel with two hard-separated domains:

- **User Dreaming** — Chronicle-grounded consolidation of user-owned
  relationship/preferences into durable Chronicle memory.
- **Self Dreaming** — Autobio-grounded staging of agent self-insight for later
  Autobio/SOUL distillation.

The implementation is shared; state, principals, evidence rules, and promotion
authority are not.

The historical journal-curation cycle is retained only as `lucid.curate`
during migration. It is no longer what "Dreaming" means in Lucid.

See `references/dreaming-kernel.md`, `references/user-dreaming.md`,
`references/self-dreaming.md`, and `references/dreaming-scheduling.md`.

## 🔧 Commands

- `lucid.user-dream` — run User Dreaming immediately.
- `lucid.self-dream` — run self-Dreaming immediately.
- `lucid.curate` — run the legacy journal curator compatibility cycle.
- `lucid.status` — inspect Dreaming run state and legacy curator state.
- `lucid.init` — initialize principal-scoped Dreaming state and register jobs.
- `lucid.update` — update the Lucid skill without deleting state.

Direct scripts:

```bash
python3 scripts/lucid_user_dream.py --json
python3 scripts/lucid_self_dream.py --json
python3 scripts/lucid_curate.py --json
```

---

## 📊 Outputs

See `SKILL.md` for outputs, journals, and persistence rules.

---

## 📄 Files

| File | Purpose |
|---|---|
| `SKILL.md` | Skill definition |
| `references/` | Supporting documentation |
| `scripts/` | Helper scripts |


## Changelog

- [2.0.2] - 2026-04-26
- Changed
- [2.0.0] - 2026-04-13
- Changed
- Added
- Removed
- [1.0.0] - 2026-04-09
- Added

---

## 📚 Documentation

Read `SKILL.md` for operational details, schemas, and validation rules.

Read `references/` for detailed specifications and examples.


---

## 📄 License

MIT License — see `LICENSE` for details.