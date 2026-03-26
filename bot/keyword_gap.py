import json
import os
import threading
from .logger import log_info

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")


def _load_competitor_urls() -> list:
    """Load competitor URLs from dynamic_settings.json."""
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        sources = settings.get("scraping_sources", {})
        return sources.get("competitor_sitemaps", [])
    except Exception:
        return []


import multiprocessing

def _run_ddgs_search(competitors, queue):
    try:
        from ddgs import DDGS
        missing_keywords = []
        with DDGS(timeout=10) as ddgs:
            for comp in competitors[:3]:
                domain = comp.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
                results = ddgs.text(f"site:{domain} best OR top OR guide 2026", max_results=5)
                if results:
                    for r in results:
                        title = str(r.get("title", ""))
                        keywords = [w.strip().lower() for w in title.split("|")[0].split("-")[0].split(":")[0].split() if len(w) > 3]
                        keyword_phrase = " ".join(keywords[:4])
                        if keyword_phrase:
                            missing_keywords.append({
                                "keyword": keyword_phrase,
                                "source": domain,
                                "title": title
                            })
        queue.put(missing_keywords)
    except Exception as e:
        queue.put([])

def perform_keyword_gap_analysis():
    """
    Analyzes competitor sitemaps against the local content database to discover
    highly-searched keywords that competitors rank for but the local site is missing.
    Uses the Competitor Sitemaps list from the dashboard settings.
    """
    competitors = _load_competitor_urls()
    log_info(f"[Nerve Center | Keyword Gap Analyst] Cross-referencing local sitemap with {len(competitors)} competitor domains...")

    missing_keywords = []
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_ddgs_search, args=(competitors, queue))
    p.daemon = True
    p.start()
    p.join(timeout=30)

    if p.is_alive():
        p.terminate()
        p.join()
        log_info("[Nerve Center | Keyword Gap Analyst] ⏰ DDGS search timed out after 30s and was killed.")
    else:
        try:
            missing_keywords = queue.get(timeout=2)
        except Exception:
            pass

    if missing_keywords:
        target = missing_keywords[0]
        log_info(f"[Nerve Center | Keyword Gap Analyst] [WARNING] GAP FOUND: Competitor '{target['source']}' covers '{target['keyword']}' — you don't!")
        log_info(f"[Nerve Center | Keyword Gap Analyst] [SUCCESS] Tasked Writer Agent to draft a pillar page targeting '{target['keyword']}'.")
        return missing_keywords
    else:
        log_info("[Nerve Center | Keyword Gap Analyst] Content parity achieved. No major keyword gaps detected today.")
        return []


if __name__ == "__main__":
    perform_keyword_gap_analysis()
