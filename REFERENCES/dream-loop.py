#!/usr/bin/env python3
"""
Lucid dream loop — nightly ingestion pipeline.
Reviews journals, decides what to file, and uses background=true to avoid timeout.
Includes Weak Signal Recirculation to promote old, deferred signals.
"""

import os
import json
from pathlib import Path
from datetime import date, datetime

def load_ingestion_log():
    log_path = Path.home() / ".hermes" / "commons" / "data" / "ocas-lucid" / "ingestion_log.jsonl"
    processed = []
    last_run = None
    if log_path.exists():
        with open(log_path, "r") as f:
            for line in f:
                entry = json.loads(line)
                if "last_run_date" in entry:
                    last_run = entry["last_run_date"]
                if "processed_paths" in entry:
                    processed.extend(entry["processed_paths"])
    return last_run, processed

def save_ingestion_log(last_run, processed):
    log_path = Path.home() / ".hermes" / "commons" / "data" / "ocas-lucid" / "ingestion_log.jsonl"
    with open(log_path, "w") as f:
        f.write(json.dumps({"last_run_date": last_run, "processed_paths": processed}) + "\n")

def scan_journals(since_date):
    journals_root = Path.home() / ".hermes" / "commons" / "journals"
    matches = []
    for d in journals_root.glob("**/*.json"):
        try:
            with open(d, "r") as f:
                entry = json.load(f)
                if "date" in entry:
                    entry_date = entry["date"]
                    if since_date is None or entry_date >= since_date:
                        matches.append(d)
        except:
            pass
    return matches

def calculate_relevance(entry):
    score = 0
    content = entry.get("content", "") or ""
    entities = entry.get("entities", [])
    
    # Decision keywords boost
    if any(word in content.lower() for word in ["decided", "agreed", "confirmed", "agreement", "resolved"]):
        score += 3
    
    # User relevance boost
    if any(ent.get("user_relevance") == "user" for ent in entities if isinstance(ent, dict)):
        score += 5
        
    return score

def classify_entry(entry):
    """Classify a journal entry and determine routing."""
    content = entry.get("content", "") or ""
    entities = entry.get("entities", [])
    
    # 1. Decision records with relationships -> Chronicle
    if entry.get("type") == "DecisionRecord" and entities:
        return "chronicle", {
            "subject": entities[0].get("id", "") if isinstance(entities[0], dict) else str(entities[0]),
            "predicate": entry.get("predicate", "has_property"),
            "object": entry.get("object", "unknown")
        }
    
    # 2. High-content verbatim -> MemPalace
    if len(content) > 100:
        return "mempalace", {
            "wing": "hermes",
            "room": "session_reflections",
            "content": content
        }
    
    return "skip", None

def file_to_chronicle(subject, predicate, object):
    from hermes_tools import mcp_mempalace_kg_add
    try:
        mcp_mempalace_kg_add(subject=subject, predicate=predicate, object=object)
        return True
    except:
        return False

def file_to_mempalace(wing, room, content):
    from hermes_tools import mcp_mempalace_check_duplicate, mcp_mempalace_add_drawer
    if mcp_mempalace_check_duplicate(content=content, threshold=0.9):
        return False
    try:
        mcp_mempalace_add_drawer(wing=wing, room=room, content=content)
        return True
    except:
        return False

def run_dream():
    last_run, processed = load_ingestion_log()
    today = date.today().isoformat()
    
    # --- PHASE 1: Fresh Scan ---
    new_files = scan_journals(since_date=last_run)
    fresh_decisions = []
    for f in new_files:
        try:
            with open(f, "r") as file_in:
                entry = json.load(file_in)
            routing, payload = classify_entry(entry)
            success = False
            if routing == "chronicle":
                success = file_to_chronicle(**payload)
            elif routing == "mempalace":
                success = file_to_mempalace(**payload)
            
            processed.append({
                "path": str(f), 
                "status": routing if success else "skip", 
                "timestamp": datetime.now().isoformat()
            })
            fresh_decisions.append({"path": str(f), "routing": routing, "success": success})
        except Exception as e:
            processed.append({"path": str(f), "status": "error", "timestamp": datetime.now().isoformat()})

    # --- PHASE 2: Recirculation ---
    recirc_decisions = []
    # Find entries skipped > 7 days ago
    now = datetime.now()
    for p in processed:
        if p["status"] == "skip":
            ts = datetime.fromisoformat(p["timestamp"])
            if (now - ts).days >= 7:
                try:
                    with open(p["path"], "r") as file_in:
                        entry = json.load(file_in)
                    
                    # Re-evaluate with relevance score and potential topical drift
                    if calculate_relevance(entry) > 5:
                        routing, payload = classify_entry(entry)
                        if routing != "skip":
                            success = False
                            if routing == "chronicle":
                                success = file_to_chronicle(**payload)
                            elif routing == "mempalace":
                                success = file_to_mempalace(**payload)
                            
                            # Update status in processed list
                            p["status"] = routing if success else "skip"
                            recirc_decisions.append({"path": p["path"], "routing": routing, "success": success})
                except:
                    pass

    # Logged Decisions
    decisions_path = Path.home() / ".hermes" / "commons" / "data" / "ocas-lucid" / "decisions.jsonl"
    with open(decisions_path, "a") as f:
        for d in fresh_decisions + recirc_decisions:
            f.write(json.dumps(d) + "\n")
    
    save_ingestion_log(today, processed)
    print(f"Lucid dream complete. Fresh: {len(fresh_decisions)}, Recirc: {len(recirc_decisions)}")

if __name__ == "__main__":
    import subprocess
    # Detach to avoid timeout
    subprocess.Popen(["python3", __file__], env=os.environ)
    print("Lucid dream loop launched in background.")
