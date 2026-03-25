import time
import threading
from duckduckgo_search import DDGS
from .logger import log_info
from .seo_agent import load_dynamic_settings

REGION_MAP = {
    "us": "us-en",
    "gb": "uk-en",
    "de": "de-de",
    "fr": "fr-fr",
    "ca": "ca-en",
    "au": "au-en",
    "in": "in-en",
    "br": "br-pt",
    "es": "es-es",
    "it": "it-it",
    "jp": "jp-jp",
    "kr": "kr-kr",
    "mx": "mx-es",
    "nl": "nl-nl",
    "se": "se-sv",
    "nz": "nz-en",
    "sg": "sg-en",
}


import multiprocessing

def _run_ddgs_news(regions, region_map, queue):
    try:
        from duckduckgo_search import DDGS
        import time
        results_list = []
        with DDGS(timeout=10) as ddgs:
            for region_code in regions:
                ddg_region = region_map.get(region_code, "us-en")
                time.sleep(2)
                try:
                    results = ddgs.news(
                        "technology OR artificial intelligence OR web development",
                        region=ddg_region,
                        max_results=5,
                    )
                    if results:
                        for r in results:
                            results_list.append({
                                "title": r.get("title", ""),
                                "source": r.get("source", ""),
                                "region": region_code,
                            })
                except Exception:
                    continue
        queue.put(results_list)
    except Exception as e:
        queue.put([])

def analyze_breakout_trends():
    """
    Connects to DuckDuckGo News API to detect trending topics in the targeted geo-regions.
    """
    settings = load_dynamic_settings()
    regions = settings.get("target_regions", ["us"])

    log_info(f"[Trend Spotter] Pinging trends across {len(regions)} regions: {', '.join(regions)}")

    all_trends = []
    
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_run_ddgs_news, args=(regions, REGION_MAP, queue))
    p.daemon = True
    p.start()
    p.join(timeout=45)

    if p.is_alive():
        p.terminate()
        p.join()
        log_info("[Trend Spotter] ⏰ تم تجاوز المهلة الزمنية (45 ثانية) وتم إنهاء العملية بالقوة. متابعة...")
    else:
        try:
            all_trends = queue.get(timeout=2)
        except Exception:
            pass

    if not all_trends:
        log_info("[Trend Spotter] لا توجد تريندات جديدة اليوم.")
        return []

    log_info(f"[Trend Spotter] ✅ تم استخراج {len(all_trends)} خبر من {len(regions)} منطقة.")

    top = all_trends[0]
    log_info(f"[Trend Spotter] [ALERT] BREAKOUT: '{top['title']}' (Trending in {top['region']})")

    return all_trends


if __name__ == "__main__":
    analyze_breakout_trends()
