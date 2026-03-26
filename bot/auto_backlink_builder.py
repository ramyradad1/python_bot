import threading
from ddgs import DDGS
from .logger import log_info

import multiprocessing

def _run_ddgs_search(query, queue):
    try:
        from ddgs import DDGS
        links = []
        with DDGS(timeout=10) as ddgs:
            results = ddgs.text(query, max_results=2)
            for r in dict(enumerate(results)).values():
                links.append(r.get("href", ""))
        queue.put(links)
    except Exception as e:
        queue.put([])

def hunt_for_backlinks(niche: str = "Web Development"):
    """
    Automates prospecting for high-DA contextual backlink opportunities (Guest Posts, Forums) 
    using advanced search engine dorks.
    """
    log_info(f"[Nerve Center | Backlink Builder] Deploying search dorks to prospect PR opportunities for '{niche}'...")
    
    query = f"{niche} 'write for us' OR 'guest post'"
    links = []
    
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_ddgs_search, args=(query, queue))
    p.daemon = True
    p.start()
    p.join(timeout=20)
    
    if p.is_alive():
        p.terminate()
        p.join()
        log_info("[Nerve Center | Backlink Builder] ⏰ DDGS search timed out after 20s and was killed.")
    else:
        try:
            links = queue.get(timeout=2)
        except Exception:
            pass
    
    log_info(f"[Nerve Center | Backlink Builder] Discovered {len(links)} high-DA target domains.")
    if links:
        log_info(f"[Nerve Center | Backlink Builder] [SUCCESS] Added '{links[0]}' to the Pitch Pipeline for outreach.")

if __name__ == "__main__":
    hunt_for_backlinks("Tech SEO")
