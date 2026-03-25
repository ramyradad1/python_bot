from .logger import log_info

def analyze_user_intent(keyword: str) -> str:
    """
    Simulates semantic NLP analysis on a keyword to determine if the searcher's intent 
    is Informational, Transactional, Navigational, or Commercial.
    """
    log_info(f"[Nerve Center | Intent Analyzer] Performing semantic NLP parsing on keyword: '{keyword}'...")
    
    intent = "Informational"
    if any(word in keyword.lower() for word in ["buy", "cheap", "price", "discount"]):
        intent = "Transactional"
    elif any(word in keyword.lower() for word in ["best", "top", "vs", "review"]):
        intent = "Commercial"
        
    log_info(f"[Nerve Center | Intent Analyzer] Detected {intent} intent. Reconfiguring Writer Agent tone parameters to match.")
    return intent

if __name__ == "__main__":
    analyze_user_intent("best cloud hosting 2026")
