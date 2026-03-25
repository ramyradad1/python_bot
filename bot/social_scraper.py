import json
import os
import threading
import requests
from .logger import log_info

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")


def _load_subreddits() -> list:
    """Load target subreddits from dynamic_settings.json."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        sources = settings.get("scraping_sources", {})
        subs = sources.get("reddit_subreddits", [])
        # Normalize: strip "r/" prefix for search queries
        return [s.replace("r/", "") for s in subs]
    except Exception:
        return ["techsupport", "webdev"]


import multiprocessing

def _run_ddgs_search(subreddits, queue):
    try:
        from duckduckgo_search import DDGS
        problems = []
        with DDGS(timeout=10) as ddgs:
            for sub in subreddits:
                query = f"site:reddit.com/r/{sub} 'how to fix' OR 'help' OR 'not working' OR 'error'"
                results = ddgs.text(query, max_results=3)
                if results:
                    for r in results:
                        problems.append({
                            "title": str(r.get("title", "")),
                            "body": str(r.get("body", "")),
                            "source": f"Reddit r/{sub}",
                            "url": str(r.get("href", ""))
                        })
        queue.put(problems)
    except Exception as e:
        queue.put([])

def fetch_trending_problems() -> list:
    """
    Fetches trending technical problems from Reddit using Free Search APIs (DuckDuckGo).
    Subreddits are loaded dynamically from the dashboard settings.
    No API keys required!
    """
    subreddits = _load_subreddits()
    log_info(f"[Social Scraper] Scanning {len(subreddits)} subreddits for trending problems via DuckDuckGo...")
    problems = []

    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_ddgs_search, args=(subreddits, queue))
    p.daemon = True
    p.start()
    p.join(timeout=30)

    if p.is_alive():
        p.terminate()
        p.join()
        log_info("[Social Scraper] ⏰ DDGS search timed out after 30s and was forcefully killed.")
    else:
        try:
            problems = queue.get(timeout=2)
        except Exception:
            pass

    if problems:
        log_info(f"[Social Scraper] Successfully extracted {len(problems)} genuine user problems from {len(subreddits)} subreddits.")
        return problems

    log_info("[Social Scraper] No results found. Returning empty list.")
    return []


if __name__ == "__main__":
    res = fetch_trending_problems()
    for p in res:
        print(p["title"])
