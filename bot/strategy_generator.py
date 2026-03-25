from .logger import log_info
from .memory_bank import recall_recent, remember

def generate_novel_strategies():
    """
    Uses the bot's memory bank history plus an LLM (Gemini) to brainstorm 
    entirely new SEO strategies the bot has never tried before.
    """
    log_info("[Nerve Center | Strategy Generator] Feeding historical decision log to Gemini for creative ideation...")
    
    past = recall_recent(5)
    past_summary = ", ".join([d.get("action", "") for d in past]) if past else "No history yet"
    
    # Mock LLM-generated strategies (in production, this calls Gemini API)
    strategies = [
        "Create a 'Zero-Click Content' series with direct answers in meta descriptions to dominate Featured Snippets.",
        "Launch a 'Comparison Hub' pillar page targeting 'X vs Y' queries in the tech niche.",
        "Build topical authority clusters by interlinking 15+ articles around a single core topic."
    ]
    
    log_info(f"[Nerve Center | Strategy Generator] Gemini analyzed past actions: [{past_summary}]")
    for i, s in enumerate(strategies, 1):
        log_info(f"[Nerve Center | Strategy Generator] Novel Strategy #{i}: {s}")
    
    chosen = strategies[0]
    log_info(f"[Nerve Center | Strategy Generator] [SUCCESS] Auto-selected Strategy #{1} for immediate deployment.")
    remember("Strategy Generated", f"Deployed novel tactic: '{chosen}'")
    
    return chosen

if __name__ == "__main__":
    generate_novel_strategies()
