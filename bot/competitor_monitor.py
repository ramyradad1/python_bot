import json
import os
import requests
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


def _fetch_sitemap_titles(base_url: str) -> list:
    """Attempt to parse titles from a competitor's sitemap."""
    articles = []
    try:
        sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
        resp = requests.get(sitemap_url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; TechnifyBot/1.0)"
        })
        if resp.status_code == 200 and "<loc>" in resp.text:
            import re
            urls = re.findall(r"<loc>(.*?)</loc>", resp.text)
            recent = urls[-5:] if len(urls) > 5 else urls
            for url in recent:
                slug = url.rstrip("/").split("/")[-1]
                title = slug.replace("-", " ").replace("_", " ").title()
                articles.append({
                    "url": url,
                    "title": title,
                    "competitor": base_url.replace("https://", "").replace("www.", "").split("/")[0]
                })
    except requests.Timeout:
        log_info(f"[Competitor Monitor] انتهت المهلة عند فحص {base_url}")
    except Exception as e:
        log_info(f"[Competitor Monitor] فشل فحص {base_url}: {e}")
    return articles


def run_competitor_monitoring():
    """
    Scans competitor sitemaps to detect newly published articles.
    Sources are loaded dynamically from dashboard settings.
    """
    competitors = _load_competitor_urls()
    if not competitors:
        log_info("[Competitor Monitor] لا توجد مواقع منافسين معرّفة. أضفها من لوحة التحكم.")
        return []

    log_info(f"[Competitor Monitor] جاري فحص {len(competitors)} موقع منافس...")

    all_new_articles = []
    for comp_url in competitors:
        found = _fetch_sitemap_titles(comp_url)
        all_new_articles.extend(found)
        if found:
            log_info(f"[Competitor Monitor] تم العثور على {len(found)} مقال من {comp_url}")

    if all_new_articles:
        top = all_new_articles[0]
        log_info(f"[Competitor Monitor] تنبيه: {top['competitor']} نشر '{top['title']}'")
        return all_new_articles
    else:
        log_info("[Competitor Monitor] لا يوجد محتوى جديد عند المنافسين اليوم.")
        return []


if __name__ == "__main__":
    run_competitor_monitoring()
