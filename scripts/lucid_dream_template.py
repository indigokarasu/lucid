#!/usr/bin/env python3
"""
Lucid Dream Cycle - Nightly Journal Curator (Production Template)
============================================================
This script implements the full dream cycle for the ocas-lucid skill.
It is designed to be written to /tmp/ and executed via terminal() in cron mode.

Usage: python3 /tmp/lucid_dream.py

Key design decisions encoded here:
1. Scan classification uses SKILL-LEVEL EXCEPTIONS (not just filename patterns)
2. Priority sorting ensures high-signal journals are processed before the 40-cap
3. MemPalace MCP calls are wrapped in try/except degraded mode
4. All records are written even in degraded mode (classification still valuable)
5. entities_observed type guard (can be int instead of list)
6. File discovery handles both date subdirs and skill-root-level files
7. Multi-batch support (process 200+ journals per run to clear scan backlogs)

Usage:
  python3 lucid_dream_template.py                 # process a batch (default 200)
  python3 lucid_dream_template.py --help          # print this usage, exit 0 (no side effects)
  python3 lucid_dream_template.py --dry-run       # classify, print, write NOTHING
  python3 lucid_dream_template.py --batch-size 40 # override the batch cap
  python3 lucid_dream_template.py --json          # machine-readable summary on stdout

Exit codes:
  0  completed (or --help)
  2  bad usage / missing required state (config.json absent)
  3  deferred dependency unavailable (filesystem roots unreadable)
"""
import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Journals processed per run when --batch-size is not given. 200 clears scan
# backlogs faster than the classic 40 cap; see SKILL.md "Multi-Batch Processing".
DEFAULT_BATCH_SIZE = 200

# === PATHS (pathlib) ===
DATA_DIR = Path(os.path.expanduser("~/.hermes/commons/data/ocas-lucid"))
JOURNALS_DIR = Path(os.path.expanduser("~/.hermes/commons/journals"))
LUCID_JOURNALS_DIR = Path(os.path.expanduser("~/.hermes/commons/journals/ocas-lucid"))
CONFIG_PATH = DATA_DIR / "config.json"
INGESTION_LOG_PATH = DATA_DIR / "ingestion_log.jsonl"
DECISIONS_PATH = DATA_DIR / "decisions.jsonl"
RECIRCULATION_PATH = DATA_DIR / "recirculation_queue.jsonl"
EVIDENCE_PATH = DATA_DIR / "evidence.jsonl"

# === SCAN CLASSIFICATION (with skill-level exceptions) ===
SCAN_PATTERNS = [
    '-scan-', '_scan_', '-scan.', '_scan.',
    '-sweep-', '_sweep_', '-sweep.', '_sweep.',
    'watch-sweep', 'deep-scan-', 'light-scan',
    'daily-', '_daily_', 'weekly-', '_weekly_',
    'journal-scan', 'forge-journal-scan', 'forge_journal_',
    'update_check_', 'conflict-scan', 'ingest-cron',
]

def is_scan(fp):
    name = fp.split('/')[-1].lower()
    # Skill-level exceptions — NEVER classify these as scans
    if 'mentor-light' in name or 'mentor-light-caller' in name:
        return False
    if '/ocas-vesper/' in fp or '/ocas-taste/' in fp:
        return False
    if 'praxis-review' in name or 'praxis-debrief' in name or 'praxis-update' in name:
        return False
    if 'dispatch-triage' in name or 'dispatch-draft' in name:
        return False
    # ocas-custodian/light-* and /deep-* files are NOT pure scans
    if '/ocas-custodian/' in fp and ('/light-' in fp or '/deep-' in fp):
        return False
    # ocas-spot/spot-* without sweep/watch are interesting
    if '/ocas-spot/' in fp:
        fname = fp.split('/')[-1].lower()
        if 'sweep' not in fname and 'watch' not in fname:
            return False
    for p in SCAN_PATTERNS:
        if p in name:
            return True
    return False

# === PRIORITY SORTING ===
SKILL_PRIORITY = {
    'ocas-mentor': 0, 'ocas-vesper': 1, 'ocas-praxis': 2, 'ocas-taste': 3,
    'ocas-dispatch': 4, 'ocas-spot': 5, 'ocas-forge': 6, 'ocas-custodian': 7,
    'ocas-elephas': 8, 'ocas-finch': 9, 'ocas-bones': 10, 'ocas-sands': 11,
    'dispatch': 50,
}

def priority_key(fp):
    """Sort key: interesting (non-scan) first, then by skill priority, then alphabetical."""
    fp_str = str(fp)
    parts = fp_str.split('/')
    try:
        skill_idx = parts.index('journals') + 1
        skill = parts[skill_idx] if skill_idx < len(parts) else ""
    except (ValueError, IndexError):
        skill = ""
    scan = is_scan(fp_str)
    return (1 if scan else 0, SKILL_PRIORITY.get(skill, 50), parts[-1])

# === NARRATIVE EXTRACTION ===
def extract_narrative(journal, filepath):
    # Some OCAS journals are a top-level JSON list, not an object. A list has no
    # .get(); without this guard one such file raises AttributeError and kills
    # the whole batch mid-run.
    if isinstance(journal, list):
        parts = []
        for item in journal:
            if isinstance(item, str) and len(item) > 10:
                parts.append(item)
            elif isinstance(item, dict):
                for k in ["summary", "description", "notes", "text", "diagnosis"]:
                    v = item.get(k)
                    if isinstance(v, str) and len(v) > 10:
                        parts.append(v)
        return " ".join(parts)[:3000]
    if not isinstance(journal, dict):
        return ""

    parts = []
    NARRATIVE_FIELDS = ["summary", "description", "reasoning_summary",
                        "findings", "analysis", "report", "notes", "text", "content"]
    for field in NARRATIVE_FIELDS:
        val = journal.get(field)
        if isinstance(val, str) and len(val) > 10:
            parts.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for k in ["diagnosis", "summary", "description", "notes", "text"]:
                        v = item.get(k)
                        if isinstance(v, str) and len(v) > 10:
                            parts.append(v)
    # Vesper: nested decision.reasoning_summary
    decision = journal.get("decision", {})
    if isinstance(decision, dict):
        rs = decision.get("reasoning_summary", "")
        if rs and isinstance(rs, str) and len(rs) > 10:
            parts.append(rs)
    # Dispatch: content.decision.reasoning_summary
    content = journal.get("content", {})
    if isinstance(content, dict):
        d = content.get("decision", {})
        if isinstance(d, dict):
            rs = d.get("reasoning_summary", "")
            if rs and isinstance(rs, str) and len(rs) > 10:
                parts.append(rs)
    return " ".join(parts)[:3000]

def extract_entities(journal, filepath):
    entities = []
    if isinstance(journal, list):
        journal = {}
    if not isinstance(journal, dict):
        return entities
    # GUARD: entities_observed can be an int (count) instead of a list
    eo_list = journal.get("entities_observed", [])
    if not isinstance(eo_list, list):
        eo_list = []
    for eo in eo_list:
        if isinstance(eo, str):
            entities.append({"name": eo, "type": "unknown"})
        elif isinstance(eo, dict):
            name = eo.get("name", eo.get("label", ""))
            if name:
                entities.append({"name": name, "type": eo.get("type", "unknown")})
    # Vesper nested entities
    decision = journal.get("decision", {})
    if isinstance(decision, dict):
        payload = decision.get("payload", {})
        if isinstance(payload, dict):
            for eo in payload.get("entities_observed", []):
                if isinstance(eo, dict):
                    name = eo.get("name", eo.get("label", ""))
                    if name:
                        entities.append({"name": name, "type": eo.get("type", "unknown")})
    # A journal that observed only its own skill name did not observe an entity.
    # `mentor-light` writes entities_observed: ["ocas-mentor"] in every single
    # run; counting that as entity_density(+2) hands pure-metrics journals a
    # free point and inflates the ledger. Drop self-references.
    skill = ""
    parts_fp = str(filepath).split("/")
    if "journals" in parts_fp:
        i = parts_fp.index("journals") + 1
        if i < len(parts_fp):
            skill = parts_fp[i]
    if skill:
        entities = [e for e in entities
                    if str(e.get("name", "")).lower() != skill.lower()]
    return entities

# === SCORING ===
def score_journal(journal, narrative, filepath):
    score = 0
    signals = []
    entities = extract_entities(journal, filepath)
    has_entities = len(entities) > 0

    # Pure metrics early exit
    if len(narrative) < 300 and not has_entities:
        return -3, ["pure_metrics(-3)"], entities

    lower = narrative.lower()

    if any(kw in lower for kw in ["learned", "correction", "mistake", "improvement",
            "should have", "could have", "better approach", "next time", "avoid",
            "fix", "resolved", "solution", "workaround"]):
        score += 4; signals.append("correction_or_lesson(+4)")

    if any(kw in lower for kw in ["decided", "decision", "chose", "selected",
            "determined", "conclusion", "recommend", "adopt", "approved", "rejected",
            "prefer", "opt for", "go with"]):
        score += 3; signals.append("decision_keywords(+3)")

    if has_entities:
        score += 2; signals.append("entity_density(+2)")

    if any(kw in lower for kw in ["blocked", "blocker", "error", "failed", "failure",
            "issue", "problem", "unavailable", "exhaustion", "limit", "rate limit",
            "429", "timeout", "crash"]) and len(narrative) > 200:
        score += 2; signals.append("blocker_context(+2)")

    if any(kw in lower for kw in ["cross-skill", "integration", "coordinated",
            "multiple skill", "skill cooperation", "inter-skill", "between skills"]):
        score += 2; signals.append("cross_skill(+2)")

    if any(kw in lower for kw in ["local_adaptation", "adapted", "customized",
            "modified", "preserved", "conflict_resolution", "merge conflict"]):
        score += 2; signals.append("adaptations(+2)")

    jtype = journal.get("journal_type", journal.get("type", "")) if isinstance(journal, dict) else ""
    if jtype in ["Action", "Interaction", "action"]:
        score += 3; signals.append("user_directed(+3)")

    if len(narrative) > 500:
        score += 1; signals.append("artifacts(+1)")

    return score, signals, entities

def classify(score):
    if score >= 5: return "file"
    if score >= 3: return "recirculate"
    return "skip"

# === WING ASSIGNMENT ===
def get_wing_room(skill):
    mapping = {
        'ocas-custodian': ('system', 'operations'),
        'ocas-mentor': ('evolution', 'evolution'),
        'ocas-finch': ('evolution', 'evolution'),
        'ocas-forge': ('evolution', 'evolution'),
        'ocas-praxis': ('evolution', 'evolution'),
        'ocas-dispatch': ('operations', 'operations'),
        'ocas-spot': ('operations', 'operations'),
        'ocas-vesper': ('operations', 'operations'),
        'ocas-taste': ('preferences', 'preferences'),
        'ocas-elephas': ('knowledge', 'knowledge'),
        'ocas-bones': ('operations', 'operations'),
        'ocas-sands': ('preferences', 'preferences'),
    }
    return mapping.get(skill, ('root', 'operations'))

# === FILE DISCOVERY ===
def gather_unprocessed(processed):
    """Gather all unprocessed journal files, handling both date subdirs and root-level files."""
    all_files = []
    for skill_dir in sorted(JOURNALS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        if skill_dir.name == "ocas-lucid":
            continue
        for date_dir in sorted(skill_dir.iterdir()):
            if not date_dir.is_dir():
                # Handle files directly in skill dir (e.g., ocas-custodian/esc-run-*)
                if date_dir.suffix == ".json" and date_dir.name != "task-list.json":
                    fp_str = str(date_dir)
                    if fp_str not in processed and "ocas-lucid" not in fp_str:
                        all_files.append(date_dir)
                continue
            for f in sorted(date_dir.glob("*.json")):
                if f.name == "task-list.json":
                    continue
                fp_str = str(f)
                if fp_str not in processed and "ocas-lucid" not in fp_str:
                    all_files.append(f)
    return all_files

# === MEMPALACE FILING (SQLite fallback) ===
def file_to_kg(entities, rel_path, skill, room, narrative_summary):
    """File entities to MemPalace KG via SQLite direct access."""
    try:
        import sqlite3
        conn = sqlite3.connect("<mempalace>/palace/knowledge_graph.sqlite3")
        c = conn.cursor()
        filed = []
        for ent in entities:
            eid = ent["name"].lower().replace(" ", "_")[:40]
            c.execute("INSERT OR IGNORE INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)",
                      (eid, ent["name"], ent["type"], json.dumps({"source": rel_path, "skill": skill})))
            tid = str(uuid.uuid4())
            c.execute("INSERT OR IGNORE INTO triples (id, subject, predicate, object, source_closet, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                      (tid, ent["name"], "is_a", ent["type"], room, rel_path))
            filed.append(ent["name"])
        # Add journal entity
        jid = rel_path.replace("/", "_").replace(".", "_")[:50]
        c.execute("INSERT OR IGNORE INTO entities (id, name, type, properties) VALUES (?, ?, ?, ?)",
                  (jid, f"journal:{rel_path}", "Document",
                   json.dumps({"skill": skill, "summary": narrative_summary[:200]})))
        c.execute("INSERT OR IGNORE INTO triples (id, subject, predicate, object, source_closet, source_file) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(uuid.uuid4()), f"journal:{rel_path}", "produced_by", skill, room, rel_path))
        conn.commit()
        conn.close()
        return filed
    except Exception as e:
        return [f"ERROR: {e}"]

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="lucid_dream_template.py",
        description="Lucid dream cycle: batch-classify OCAS journals and file the high-relevance ones.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                   help=f"journals to process this run (default: {DEFAULT_BATCH_SIZE})")
    p.add_argument("--dry-run", action="store_true",
                   help="classify and print, but write no journal/log/config/cursor state")
    p.add_argument("--json", action="store_true",
                   help="emit the run summary as JSON on stdout")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.batch_size < 1:
        print("error: --batch-size must be >= 1", file=sys.stderr)
        return 2
    if not CONFIG_PATH.exists():
        print(f"error: {CONFIG_PATH} not found. Run 'lucid.init' before the first dream cycle.",
              file=sys.stderr)
        return 2

    run_id = f"dream-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}Z"
    timestamp = datetime.now(timezone.utc).isoformat()
    dry_run = args.dry_run
    if not dry_run:
        os.makedirs(LUCID_JOURNALS_DIR, exist_ok=True)
        os.makedirs(DATA_DIR / "staging", exist_ok=True)

    # Read config & processed
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: could not read {CONFIG_PATH}: {e}", file=sys.stderr)
        return 2

    processed = set()
    if INGESTION_LOG_PATH.exists():
        for line in INGESTION_LOG_PATH.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                processed.add(entry.get("file") or entry.get("filepath") or entry.get("journal_file", ""))
            except json.JSONDecodeError:
                pass

    # Gather & sort
    all_files = gather_unprocessed(processed)
    total_available = len(all_files)
    all_files.sort(key=priority_key)

    # Content-aware pre-screen. Priority sort alone is NOT enough: `mentor-light`
    # is priority 0 AND is_scan()==False, so it owns the front of the ordering
    # and can fill an entire batch. Those journals are pure metrics (no
    # narrative, self-referential entities) and cap out at score 2, below the
    # file threshold of 5 -- so such a batch is structurally guaranteed to file
    # nothing while hiding every journal that would actually file.
    # Screening them out of SELECTION loses nothing: they still classify as
    # pure_metrics, they just stop consuming the batch budget.
    content_capable = []
    empty_screened = 0
    for f in all_files:
        try:
            with open(f) as fh:
                probe = json.load(fh)
        except Exception:
            empty_screened += 1
            continue
        if len(extract_narrative(probe, str(f))) == 0 and \
                not extract_entities(probe, str(f)):
            empty_screened += 1
            continue
        content_capable.append(f)

    # Order the batch by expected value, not just by static skill priority.
    # Pre-screening alone is not sufficient: ~70% of content-capable journals
    # still score exactly 2 (entity_density only), and the position-based order
    # puts all of them at the front, starving the handful that reach the file
    # threshold of 5. Score-ordering the batch surfaces those instead.
    # Journals that will classify as `skip` are fungible -- they skip whether
    # they are processed now or a hundred runs from now -- so deferring them
    # costs nothing, while a `file` decision deferred is a decision lost.
    def _probe(f):
        try:
            with open(f) as fh:
                pj = json.load(fh)
        except Exception:
            return -4
        pnar = extract_narrative(pj, str(f))
        pscore, _, _ = score_journal(pj, pnar, str(f))
        return pscore

    content_capable.sort(key=lambda f: (-_probe(f), priority_key(f)))

    # Process up to --batch-size journals per run (default 200) to clear scan backlogs
    to_process = content_capable[:args.batch_size]

    # Classify
    results = []
    for fp in to_process:
        try:
            with open(fp) as f:
                journal = json.load(f)
        except Exception as e:
            results.append((fp, None, -3, [f"read_error: {e}"], "skip", [], 0))
            continue
        narrative = extract_narrative(journal, str(fp))
        score, signals, entities = score_journal(journal, narrative, str(fp))
        cls = classify(score)
        results.append((fp, journal, score, signals, cls, entities, len(narrative)))

    # Write records
    decisions, ingestions, recircs = [], [], []
    filed = skipped = recirculated = 0
    file_details = []
    curated_entries = []

    for fp, journal, score, signals, cls, entities, narrative_len in results:
        rel = str(fp).replace(str(JOURNALS_DIR) + "/", "")
        parts = str(fp).split('/')
        try:
            skill_idx = parts.index('journals') + 1
            skill = parts[skill_idx] if skill_idx < len(parts) else "unknown"
        except (ValueError, IndexError):
            skill = "unknown"

        d = {
            "timestamp": timestamp, "run_id": run_id, "filepath": str(fp),
            "relative_path": rel, "score": score, "classification": cls,
            "reasoning": "; ".join(signals) if signals else "no signals",
            "signals": signals, "mempalace_filed": False, "mempalace_error": None,
            "skill": skill, "entity_count": len(entities),
            "narrative_len": narrative_len
        }
        ing = {"run_id": run_id, "file": str(fp), "processed_at": timestamp,
               "classification": cls, "score": score}

        if cls == "file":
            filed += 1
            wing, room = get_wing_room(skill)
            d["wing"] = wing
            d["room"] = room
            d["mempalace_error"] = "pending_mcp"
            file_details.append({
                "path": rel, "score": score, "signals": signals,
                "skill": skill, "wing": wing, "room": room,
                "entities": entities, "narrative_len": narrative_len
            })
            # The narrative itself is NOT stored in the decision record — only
            # its length. If filing to MemPalace is unavailable, a `file`
            # decision would point at nothing retrievable. Write the payload to
            # a curated journal file now, so a classification always has a
            # durable artifact behind it.
            narrated = journal if isinstance(journal, dict) else {}
            _nar = extract_narrative(journal, str(fp)) if journal is not None else ""
            try:
                _safe = rel.replace("/", "_").replace(".json", "")
                _cpath = LUCID_JOURNALS_DIR / today / f"curated-{run_id}-{_safe}.json"
                os.makedirs(_cpath.parent, exist_ok=True)
                with open(_cpath, "w") as _cf:
                    json.dump({
                        "journal_spec_version": "1.3", "run_id": run_id,
                        "timestamp": timestamp, "type": "Action",
                        "source_journal": rel, "skill": skill,
                        "wing": wing, "room": room, "relevance_score": score,
                        "signals": signals, "summary": _nar[:600],
                        "narrative": _nar or "(no narrative field; classified on structured signals only)",
                        "entities": entities, "entity_count": len(entities),
                        "filed_via": "curated_journal_file",
                        "mempalace_available": False,
                        "note": "MemPalace unavailable; this file is the filing payload for Chronicle ingestion.",
                    }, _cf, indent=2)
                curated_entries.append(_cpath.name)
                d["mempalace_filed"] = True
                d["mempalace_error"] = None
                d["filed_via"] = "curated_journal_file"
            except Exception as _e:
                d["mempalace_error"] = f"curated_write_failed: {_e}"[:200]
        elif cls == "recirculate":
            recirculated += 1
            recircs.append({
                "filepath": str(fp), "relative_path": rel, "score": score,
                "reasoning": "; ".join(signals), "re_evaluations": 0,
                "first_seen": timestamp, "last_evaluated": timestamp,
                "skill": skill
            })
        else:
            skipped += 1

        decisions.append(d)
        ingestions.append(ing)  # FIXED: was 'ig' (typo)

    # Append to data files. --dry-run writes nothing at all.
    if not dry_run:
        with open(DECISIONS_PATH, 'a') as f:
            for d in decisions:
                f.write(json.dumps(d) + "\n")
        with open(INGESTION_LOG_PATH, 'a') as f:
            for ig in ingestions:
                f.write(json.dumps(ig) + "\n")
        with open(RECIRCULATION_PATH, 'a') as f:
            for r in recircs:
                f.write(json.dumps(r) + "\n")

    # File to MemPalace KG (SQLite fallback when MCP unavailable).
    # Never touch the external store on a dry run.
    # Only downgrade: a curated entry written above is a real durable filing,
    # so never reset its state back to "not filed" on the MemPalace path.
    mempalace_filed_count = 0
    for fd in (() if dry_run else file_details):
        wing, room = fd["wing"], fd["room"]
        summary = fd["signals"]
        filed_entities = file_to_kg(fd["entities"], fd["path"], fd["skill"], room, str(summary))
        if filed_entities and not any(str(e).startswith("ERROR") for e in filed_entities):
            mempalace_filed_count += 1
            # Update the decision record
            for d in decisions:
                if d["filepath"] == str(Path(JOURNALS_DIR) / fd["path"]):
                    d["mempalace_filed"] = True
                    d["mempalace_error"] = None
                    d["filed_via"] = "mempalace_kg"

    # A `file` decision is only real if something retrievable was written.
    filed_count = max(mempalace_filed_count, len(curated_entries))

    # Evidence
    evidence = {
        "timestamp": timestamp, "run_id": run_id, "dream_cycle": True,
        "mode": "cron", "journals_scanned": len(results),
        "total_journals": total_available, "file_count": filed,
        "recirculate_count": recirculated, "skip_count": skipped,
        "filed_count": filed_count,
        "curated_entries_written": len(curated_entries),
        "degraded": "mempalace" if curated_entries and not mempalace_filed_count else None,
        "empty_journals_screened_from_selection": empty_screened,
        "not_activity_reason": None
    }
    if not dry_run:
        with open(EVIDENCE_PATH, 'a') as f:
            f.write(json.dumps(evidence) + "\n")

    # Dream journal
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    run_dir = LUCID_JOURNALS_DIR / today

    dream = {
        "journal_spec_version": "1.3", "run_id": run_id, "timestamp": timestamp,
        "type": "Action",
        "summary": (
            f"Dream {run_id}: {len(results)} journals from {total_available} available. "
            f"Filed {filed} (curated entries written: {len(curated_entries)}), "
            f"recirculated {recirculated}, skipped {skipped}. "
            f"Empty journals screened from selection: {empty_screened}."
            + (" MemPalace unavailable; filing deferred to curated journal files."
               if curated_entries and not mempalace_filed_count else "")
        ),
        "scan_count": len(results), "file_count": filed,
        "recirculate_count": recirculated, "skip_count": skipped,
        "filed_count": filed_count,
        "curated_entries_written": curated_entries,
        "mempalace_available": mempalace_filed_count > 0,
        "total_journals": total_available, "file_details": file_details,
        "recirculate_details": [], "skip_details": [],
        "re_emergence_events": [], "signal_emissions": [],
        "not_activity_reason": "dry_run" if dry_run else None
    }
    if not dry_run:
        os.makedirs(run_dir, exist_ok=True)
        with open(run_dir / f"{run_id}.json", 'w') as f:
            json.dump(dream, f, indent=2)

    # Update config (cursor + counters). --dry-run mutates none of this.
    if not dry_run:
        if results:
            last = results[-1][0]
            config["cursor"] = str(last)
            try:
                config["cursor_file"] = str(last.relative_to(JOURNALS_DIR))
            except ValueError:
                config["cursor_file"] = str(last)
        config["last_run"] = timestamp
        config["last_run_status"] = "complete"
        config["streak"] = config.get("streak", 0) + 1
        config["total_filed"] = config.get("total_filed", 0) + filed
        config["total_skipped"] = config.get("total_skipped", 0) + skipped
        config["total_recirculated"] = config.get("total_recirculated", 0) + recirculated

        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)

    summary = {
        "run_id": run_id, "processed": len(results), "available": total_available,
        "filed": filed, "recirculated": recirculated, "skipped": skipped,
        "mempalace_filed": mempalace_filed_count, "cursor": config.get("cursor_file"),
        "streak": config.get("streak"), "dry_run": dry_run,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}Dream {run_id}: {len(results)} processed ({filed} file, {recirculated} recirc, {skipped} skip) from {total_available} available")
        print(f"Cursor: {config.get('cursor_file', 'N/A')}")
        print(f"Streak: {config['streak']}")
        if file_details:
            print("\nFiled journals:")
            for fd in file_details:
                print(f"  [{fd['score']}] {fd['path']} -> {fd['wing']}/{fd['room']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
