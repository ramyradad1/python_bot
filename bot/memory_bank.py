import json
import os
from datetime import datetime
from .logger import log_info

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "bot_memory.json")

def _load_memory() -> list:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Auto-prune entries older than 30 days
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        data = [e for e in data if e.get("timestamp", "") > cutoff]
        return data
    return []

def _save_memory(memory: list):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False, default=str)

def remember(action: str, result: str, context: dict = None):
    """
    Persist an autonomous decision to the long-term memory bank.
    Each entry contains: timestamp, action taken, result observed, and optional context data.
    """
    memory = _load_memory()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "result": result,
        "context": context or {}
    }
    memory.append(entry)
    _save_memory(memory)
    log_info(f"[Nerve Center | Memory Bank] Stored decision: '{action}' -> Result: '{result}'")

def recall_recent(n: int = 10) -> list:
    """Recall the most recent N decisions from the memory bank."""
    memory = _load_memory()
    recent = memory[-n:]
    log_info(f"[Nerve Center | Memory Bank] Recalled {len(recent)} recent decisions from long-term storage.")
    return recent

def get_memory_stats() -> dict:
    """Get summary statistics of the memory bank."""
    memory = _load_memory()
    return {
        "total_decisions": len(memory),
        "first_entry": memory[0]["timestamp"] if memory else "N/A",
        "last_entry": memory[-1]["timestamp"] if memory else "N/A"
    }

if __name__ == "__main__":
    remember("Changed keyword density", "Traffic increased 12%", {"old": 2.0, "new": 3.0})
    print(recall_recent(5))
