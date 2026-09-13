#!/usr/bin/env python3
"""
Lucid Dream Cycle Runner
Batch-processes OCAS skill journals via relevance classification and writes curated content to journal files.

Usage:
  python3 -m scripts.lucid_run [--force] [--since YYYYMMDD] [--dry-run] [--json] [--self-update]
  python3 -m scripts.lucid_run --help

Exit codes:
  0  Success
  1  General error
  2  Usage error (bad args)
  3  Dependency missing (mempalace not installed)
  4  MemPalace unavailable (degraded mode)
"""

import argparse
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

# Guard --help before any side effects
if '--help' in sys.argv[1:] or '-h' in sys.argv[1:]:
    print(__doc__)
    sys.exit(0)

# Lazy imports for --help speed
try:
    import yaml
except ImportError:
    print("ERROR: pyyaml not installed", file=sys.stderr)
    sys.exit(3)

try:
    from mempalace.mcp_server import (
        tool_status,
        tool_check_duplicate,
        tool_add_drawer,
        tool_kg_add,
        tool_search
    )
except ImportError:
    print("ERROR: mempalace package not installed", file=sys.stderr)
    sys.exit(3)

# ============ Config & Paths ============

COMMONS_DIR = Path.home() / '.hermes' / 'commons'
CONFIG_PATH = COMMONS_DIR / 'data' / 'ocas-lucid' / 'config.json'
JOURNALS_DIR = COMMONS_DIR / 'journals'
LUCID_JOURNALS_DIR = JOURNALS_DIR / 'ocas-lucid'
MEMPALACE_PATH = Path.home() / '.mempalace' / 'palace'

DEFAULT_CONFIG = {
    'cursor': '',
    'hibernation_days': 7,
    'catchup_cap': 40,
    'exclude_self': True,
    'scoring_thresholds': {'file': 5, 'recirculate_min': 3, 'skip_max': 2},
    'reemergence_min_days': 14,
    'reemergence_max_queue_size': 200,
    'reemergence_batch_size': 20,
    'max_drawers_per_run': 20,
    'max_kg_per_run': 30,
    'okr': {
        'filing_rate_target': 0.15,
        'reemergence_promotion_target': 0.10,
        'duplicate_rate_max': 0.01,
        'kg_density_target': 0.5,
        'new_room_rate_max': 0.05,
        'success_rate_target': 0.99,
        'latency_p95_max_seconds': 120,
        'evaluation_window_entries': 90
    },
    'self_update': {
        'enabled': True,
        'check_days': 7,
        'auto_apply': True,
        'require_ff_only': True,
        'validate_before_apply': True
    }
}

# ============ Utility Functions ============

def load_config() -> Dict[str, Any]:
    """Load config.json, creating with defaults if missing."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            user_config = json.load(f)
        # Deep merge defaults
        config = DEFAULT_CONFIG.copy()
        for k, v in user_config.items():
            if isinstance(v, dict) and k in config:
                config[k].update(v)
            else:
                config[k] = v
        return config
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Write config.json atomically."""
    tmp = CONFIG_PATH.with_suffix('.tmp')
    with open(tmp, 'w') as f:
        json.dump(config, f, indent=2)
    tmp.replace(CONFIG_PATH)


def extract_timestamp_suffix(filename: str) -> Optional[str]:
    """Extract YYYYMMDDTHHMMSSZ or ISO-with-colons suffix from journal filename."""
    # Standard: skill-YYYYMMDDTHHMMSSZ.json
    import re
    m = re.search(r'(\d{8}T\d{6}Z)', filename)
    if m:
        return m.group(1)
    # ISO with colons: skill-YYYY-MM-DDTHH:MM:SSZ.json
    m = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', filename)
    if m:
        # Normalize to compact form for lexicographic comparison
        return m.group(1).replace('-', '').replace(':', '')
    return None


def scan_journals(config: Dict[str, Any], force: bool = False, since: Optional[str] = None) -> List[Path]:
    """Scan for journals newer than cursor (or since date if force)."""
    journals = []
    cursor = '' if force else config.get('cursor', '')
    cursor_suffix = extract_timestamp_suffix(cursor) if cursor else ''
    
    if since:
        since_suffix = since.replace('-', '') + 'T000000Z'
    else:
        since_suffix = cursor_suffix
    
    exclude_self = config.get('exclude_self', True)
    catchup_cap = config.get('catchup_cap', 40)
    
    for journal_file in JOURNALS_DIR.rglob('*.json'):
        if exclude_self and 'ocas-lucid' in journal_file.parts:
            continue
        suffix = extract_timestamp_suffix(journal_file.name)
        if suffix and suffix > since_suffix:
            journals.append(journal_file)
    
    # Sort by timestamp ascending (oldest first)
    journals.sort(key=lambda p: extract_timestamp_suffix(p.name) or '')
    return journals[:catchup_cap]


def extract_narrative(journal: Dict[str, Any]) -> str:
    """Extract narrative text from priority fields only."""
    parts = []
    decision = journal.get('decision', {})
    action = journal.get('action', {})
    
    # Priority order from classification.md
    for key in ['summary', 'description', 'reasoning_summary']:
        if decision.get(key):
            parts.append(str(decision[key]))
    for key in ['side_effect_intent', 'reason']:
        if action.get(key):
            parts.append(str(action[key]))
    for issue in journal.get('urgent_issues', []):
        if issue.get('summary'):
            parts.append(str(issue['summary']))
    for anomaly in journal.get('anomalies', []):
        if anomaly.get('summary'):
            parts.append(str(anomaly['summary']))
    
    return ' '.join(parts)


def score_journal(narrative: str, source_skill: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Score a journal's narrative text. Returns {score, signals, penalties}."""
    score = 0
    signals = []
    penalties = []
    text_lower = narrative.lower()
    
    # Decision keywords (+3)
    decision_kw = ['decided', 'confirmed', 'agreed', 'resolved', 'committed', 'approved', 'rejected']
    if any(kw in text_lower for kw in decision_kw):
        score += 3
        signals.append('decision_keywords')
    
    # Entity density (+2) - simplified: count capitalized words
    import re
    entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', narrative)
    if len(set(entities)) >= 3:
        score += 2
        signals.append('entity_density')
    
    # Novel entities (+3) - check MemPalace
    # TODO: implement mempalace_search for each entity
    # For now, skip - requires palace to be available
    
    # Correction/lesson (+4) - narrative only
    lesson_kw = ['mistake', 'lesson', 'learned', 'corrected', 'wrong', 'fixed', 'should have']
    if any(kw in text_lower for kw in lesson_kw):
        score += 4
        signals.append('correction_lesson')
    
    # User-directed action (+3)
    user_kw = ['user asked', 'operator directed', 'on behalf of', 'directed by']
    if any(kw in text_lower for kw in user_kw):
        score += 3
        signals.append('user_directed')
    
    # Emotional signal (+2)
    emo_kw = ['frustrated', 'impressed', 'surprised', 'disappointed', 'pleased', 'grateful']
    if any(kw in text_lower for kw in emo_kw):
        score += 2
        signals.append('emotional_signal')
    
    # Cross-skill reference (+2) - simplified check
    if any(skill in text_lower for skill in ['ocas-', 'mentor', 'forge', 'custodian', 'sift', 'dispatch']):
        if source_skill not in text_lower:  # references OTHER skill
            score += 2
            signals.append('cross_skill_reference')
    
    # Relationship signal (+3)
    rel_kw = ['works with', 'collaborates with', 'reports to', 'manages', 'partner', 'colleague']
    if any(kw in text_lower for kw in rel_kw):
        score += 3
        signals.append('relationship_signal')
    
    # Penalties
    # Pure metrics (-3)
    if len(narrative.strip()) < 50 and not any(s in signals for s in ['decision_keywords', 'correction_lesson']):
        score -= 3
        penalties.append('pure_metrics')
    
    # Routine health check (-4)
    if source_skill == 'ocas-custodian' and journal.get('event_type') == 'routine_health_check':
        score -= 4
        penalties.append('routine_health_check')
    
    return {'score': score, 'signals': signals, 'penalties': penalties}


def classify_journal(journal_path: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    """Load journal, extract narrative, score, and return classification decision."""
    with open(journal_path) as f:
        journal = json.load(f)
    
    source_skill = journal_path.parent.name
    narrative = extract_narrative(journal)
    scoring = score_journal(narrative, source_skill, config)
    score = scoring['score']
    
    thresholds = config.get('scoring_thresholds', {'file': 5, 'recirculate_min': 3, 'skip_max': 2})
    
    if score >= thresholds['file']:
        decision = 'file'
    elif score >= thresholds['recirculate_min']:
        decision = 'recirculate'
    else:
        decision = 'skip'
    
    # Wing assignment by source skill domain
    wing_map = {
        'ocas-mentor': 'skill-improvement',
        'ocas-forge': 'skill-architecture',
        'ocas-custodian': 'system-health',
        'ocas-sift': 'research',
        'ocas-dispatch': 'communication',
        'ocas-scout': 'intelligence',
        'ocas-rally': 'portfolio',
        'ocas-bones': 'prediction',
        'ocas-taste': 'preference',
        'ocas-weave': 'social-graph',
        'ocas-voyage': 'travel',
        'ocas-spot': 'appointments',
        'ocas-genie': 'storage',
        'ocas-bower': 'organization',
        'ocas-reach': 'world-data',
        'ocas-imagine': 'generative-art',
        'ocas-haiku': 'creative',
        'ocas-autobio': 'identity',
        'ocas-fellow': 'experimentation',
        'ocas-inception': 'simulation',
        'ocas-multipass': 'tool-bridge',
        'ocas-praxis': 'behavioral-refinement',
        'ocas-vibes': 'voice',
        'ocas-sands': 'calendar',
        'ocas-tasks': 'task-management',
        'ocas-usercontext': 'context',
        'ocas-vesper': 'briefing',
        'ocas-look': 'vision',
        'ocas-lucid': 'memory',
        'ocas-styx': 'transactions',
        'ocas-closure-troubleshooting': 'diagnostics',
        'ocas-10xeng': 'engineering',
        'ocas-10xeng-audit': 'engineering',
        'ocas-10xeng-autofix': 'engineering',
        'ocas-10xeng-debt': 'engineering',
        'ocas-10xeng-help': 'engineering',
        'ocas-10xeng-review': 'engineering',
        'ocas-skilllab': 'skill-maintenance',
    }
    wing = wing_map.get(source_skill, 'general')
    room = source_skill.replace('ocas-', '')
    
    return {
        'file_path': str(journal_path),
        'source_skill': source_skill,
        'score': score,
        'decision': decision,
        'wing': wing,
        'room': room,
        'narrative': narrative,
        'signals': scoring['signals'],
        'penalties': scoring['penalties'],
        'kg_triples': []  # TODO: extract from narrative
    }


def write_dream_journal(run_id: str, stats: Dict[str, Any], mode: str = 'normal', 
                        mempalace_available: bool = True, signals: List[Dict] = None) -> Path:
    """Write dream journal entry."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    run_dir = LUCID_JOURNALS_DIR / today
    run_dir.mkdir(parents=True, exist_ok=True)
    
    entry = {
        'journal_spec_version': '1.3',
        'run_id': run_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'mode': mode,
        'mempalace_available': mempalace_available,
        'mempalace_actual_calls': stats.get('mempalace_calls', 0),
        'scan_count': stats.get('scan_count', 0),
        'file_count': stats.get('file_count', 0),
        'recirculate_count': stats.get('recirculate_count', 0),
        'skip_count': stats.get('skip_count', 0),
        'reemergence_events': stats.get('reemergence_events', []),
        'signals': signals or [],
        'pending_mempalace': stats.get('pending_mempalace', 0),
        'skip_path': stats.get('skip_path')
    }
    
    journal_path = run_dir / f'{run_id}.json'
    with open(journal_path, 'w') as f:
        json.dump(entry, f, indent=2)
    return journal_path


def append_decisions(records: List[Dict[str, Any]]) -> None:
    """Append DecisionRecords to decisions.jsonl."""
    decisions_path = COMMONS_DIR / 'data' / 'ocas-lucid' / 'decisions.jsonl'
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    with open(decisions_path, 'a') as f:
        for r in records:
            f.write(json.dumps(r) + '\n')


def append_ingestion_log(stats: Dict[str, Any]) -> None:
    """Append run summary to ingestion_log.jsonl."""
    log_path = COMMONS_DIR / 'data' / 'ocas-lucid' / 'ingestion_log.jsonl'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'a') as f:
        f.write(json.dumps(stats) + '\n')


def append_recirculation(entries: List[Dict[str, Any]]) -> None:
    """Append to recirculation_queue.jsonl."""
    queue_path = COMMONS_DIR / 'data' / 'ocas-lucid' / 'recirculation_queue.jsonl'
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, 'a') as f:
        for e in entries:
            f.write(json.dumps(e) + '\n')


def check_duplicates_and_file(classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check duplicates via MemPalace and file drawers + KG."""
    results = {
        'filed': 0,
        'skipped_duplicate': 0,
        'kg_added': 0,
        'errors': []
    }
    
    for cls in classifications:
        if cls['decision'] != 'file':
            continue
        
        try:
            # Check duplicate
            dup_result = tool_check_duplicate(cls['narrative'], threshold=0.9)
            if dup_result.get('is_duplicate'):
                results['skipped_duplicate'] += 1
                # Log duplicate decision
                append_decisions([{
                    'run_id': f'lucid-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'source_file': cls['file_path'],
                    'decision': 'skip',
                    'reason': 'duplicate',
                    'score': cls['score'],
                    'duplicate_match': dup_result.get('matches', [])
                }])
                continue
            
            # File drawer
            tool_add_drawer(
                wing=cls['wing'],
                room=cls['room'],
                content=cls['narrative'],
                source_file=cls['file_path'],
                added_by='mcp'
            )
            results['filed'] += 1
            results['mempalace_calls'] = results.get('mempalace_calls', 0) + 1
            
            # File KG triples
            for triple in cls.get('kg_triples', []):
                tool_kg_add(
                    subject=triple['subject'],
                    predicate=triple['predicate'],
                    object=triple['object'],
                    valid_from=triple.get('valid_from'),
                    source_closet=triple.get('source_closet')
                )
                results['kg_added'] += 1
                results['mempalace_calls'] = results.get('mempalace_calls', 0) + 1
            
            # Log success decision
            append_decisions([{
                'run_id': f'lucid-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'source_file': cls['file_path'],
                'decision': 'file',
                'wing': cls['wing'],
                'room': cls['room'],
                'score': cls['score'],
                'kg_triples': len(cls.get('kg_triples', []))
            }])
            
        except Exception as e:
            results['errors'].append({'file': cls['file_path'], 'error': str(e)})
    
    return results


def run_reemergence(config: Dict[str, Any]) -> List[Dict]:
    """Process recirculation queue for re-emergence."""
    queue_path = COMMONS_DIR / 'data' / 'ocas-lucid' / 'recirculation_queue.jsonl'
    if not queue_path.exists():
        return []
    
    entries = []
    with open(queue_path) as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    
    # Filter by min_days
    min_days = config.get('reemergence_min_days', 14)
    now = datetime.now(timezone.utc)
    eligible = []
    remaining = []
    
    for e in entries:
        try:
            entry_time = datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00'))
            if (now - entry_time).days >= min_days:
                eligible.append(e)
            else:
                remaining.append(e)
        except:
            remaining.append(e)
    
    # Re-score eligible
    promoted = []
    requeued = []
    removed = []
    
    for e in eligible[:config.get('reemergence_batch_size', 20)]:
        try:
            jpath = Path(e['file_path'])
            if jpath.exists():
                cls = classify_journal(jpath, config)
                if cls['decision'] == 'file':
                    promoted.append(cls)
                elif cls['decision'] == 'recirculate':
                    requeued.append(e)
                else:
                    removed.append(e)
            else:
                removed.append(e)
        except:
            removed.append(e)
    
    # Rewrite queue with remaining + requeued
    all_remaining = remaining + requeued
    # Trim to max size
    if len(all_remaining) > config.get('reemergence_max_queue_size', 200):
        all_remaining = all_remaining[-config['reemergence_max_queue_size']:]
    
    with open(queue_path, 'w') as f:
        for e in all_remaining:
            f.write(json.dumps(e) + '\n')
    
    # Write removed
    if removed:
        removed_path = COMMONS_DIR / 'data' / 'ocas-lucid' / 'removed_entries.jsonl'
        with open(removed_path, 'a') as f:
            for e in removed:
                f.write(json.dumps({**e, 'removed_reason': 'reemergence_skip', 'removed_at': datetime.now(timezone.utc).isoformat()}) + '\n')
    
    return promoted


def main():
    parser = argparse.ArgumentParser(description='Lucid Dream Cycle Runner', add_help=False)
    parser.add_argument('--force', action='store_true', help='Process all journals since epoch (ignore cursor)')
    parser.add_argument('--since', type=str, help='Process journals after date (YYYYMMDD)')
    parser.add_argument('--dry-run', action='store_true', help='Scan and classify only, no filing, no cursor update')
    parser.add_argument('--json', action='store_true', help='Emit structured JSON to stdout')
    parser.add_argument('--self-update', action='store_true', help='Check and apply skill repo updates')
    parser.add_argument('--help', '-h', action='help', help='Show this help message and exit')
    args = parser.parse_args()
    
    run_id = f'lucid-{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}'
    config = load_config()
    signals = []
    stats = {
        'scan_count': 0,
        'file_count': 0,
        'recirculate_count': 0,
        'skip_count': 0,
        'mempalace_calls': 0,
        'pending_mempalace': 0,
        'reemergence_events': []
    }
    
    # Check MemPalace availability
    mempalace_available = True
    try:
        status = tool_status()
        mempalace_available = status.get('available', True)
    except Exception:
        mempalace_available = False
    
    if not mempalace_available:
        stats['pending_mempalace'] = 1  # placeholder
        mode = 'degraded: mempalace'
        stats['skip_path'] = 'MemPalace unavailable'
    else:
        mode = 'normal'
    
    # Scan journals
    journals = scan_journals(config, force=args.force, since=args.since)
    stats['scan_count'] = len(journals)
    
    if not journals:
        # No journals to process
        if not args.force and config.get('cursor'):
            # Hibernation check
            last_run = config.get('last_successful_run')
            if last_run:
                last_dt = datetime.fromisoformat(last_run.replace('Z', '+00:00'))
                if (datetime.now(timezone.utc) - last_dt).days >= config.get('hibernation_days', 7):
                    mode = 'hibernation'
                    stats['skip_path'] = f'no new journals for {config["hibernation_days"]} days'
    
    # Classify
    classifications = []
    for j in journals:
        cls = classify_journal(j, config)
        classifications.append(cls)
        if cls['decision'] == 'file':
            stats['file_count'] += 1
        elif cls['decision'] == 'recirculate':
            stats['recirculate_count'] += 1
        else:
            stats['skip_count'] += 1
    
    # Re-emergence pass
    promoted = run_reemergence(config)
    for p in promoted:
        classifications.append(p)
        stats['file_count'] += 1
        stats['reemergence_events'].append({'source_file': p['file_path'], 'score': p['score']})
    
    # File (if not dry-run and MemPalace available)
    if not args.dry_run and mempalace_available and classifications:
        file_results = check_duplicates_and_file(classifications)
        stats.update(file_results)
    
    # Update cursor (only on successful non-dry-run)
    if not args.dry_run and mempalace_available and journals:
        config['cursor'] = journals[-1].name
        config['last_successful_run'] = datetime.now(timezone.utc).isoformat()
        save_config(config)
    
    # OKR evaluation (quarterly)
    # TODO: implement
    
    # Write dream journal
    journal_path = write_dream_journal(run_id, stats, mode, mempalace_available, signals)
    
    # Log ingestion
    append_ingestion_log({
        'run_id': run_id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'mode': mode,
        **stats
    })
    
    # Output
    if args.json:
        print(json.dumps({
            'run_id': run_id,
            'mode': mode,
            'stats': stats,
            'dream_journal': str(journal_path)
        }))
    else:
        print(f'Lucid run {run_id} complete: {stats["scan_count"]} scanned, {stats["file_count"]} filed, {stats["recirculate_count"]} recirculated, {stats["skip_count"]} skipped')
        print(f'Dream journal: {journal_path}')
    
    # Exit code
    if not mempalace_available:
        sys.exit(4)
    if stats.get('errors'):
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()