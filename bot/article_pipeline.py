"""
Article Pipeline: The CORE publishing engine.
Scrapes ALL 3 source categories → Scores articles → Rewrites with AI → Publishes to Supabase.
"""
import os
import json
import time
import random
from .logger import log_info
from .scraper import scrape_latest_links, scrape_article, scrape_reddit_links, scrape_rss_links
from .publisher import process_scraped_data, is_url_processed
from .seo_agent import load_dynamic_settings
from .config import load_config

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")


def _gather_all_links(settings: dict, config: dict) -> list[dict]:
    """
    Gather links from ALL 3 source categories equally:
    1. Competitor Sitemaps (web scraping)
    2. Reddit Subreddits (trending tech discussions)
    3. RSS Feeds (direct news feeds)
    
    Returns a list of dicts: [{"url": "...", "source_type": "sitemap|reddit|rss"}]
    """
    scraping = settings.get("scraping_sources", {})
    all_links = []
    
    # === Category 1: Competitor Sitemaps ===
    sitemaps = scraping.get("competitor_sitemaps", [])
    random.shuffle(sitemaps)
    for source_url in sitemaps[:8]:  # Cap at 8 to avoid timeout
        try:
            log_info(f"[Pipeline] 🌐 Sitemaps: {source_url}")
            links = scrape_latest_links(source_url, max_links=3)
            for link in links:
                all_links.append({"url": link, "source_type": "sitemap"})
        except Exception as e:
            log_info(f"[Pipeline]   ❌ {e}")
    
    # === Category 2: Reddit ===
    subreddits = scraping.get("reddit_subreddits", [])
    random.shuffle(subreddits)
    for sub in subreddits[:3]:  # Cap at 3
        try:
            log_info(f"[Pipeline] 🟠 Reddit: {sub}")
            links = scrape_reddit_links(sub, max_links=3)
            for link in links:
                all_links.append({"url": link, "source_type": "reddit"})
        except Exception as e:
            log_info(f"[Pipeline]   ❌ {e}")
    
    # === Category 3: RSS Feeds ===
    feeds = scraping.get("rss_feeds", [])
    random.shuffle(feeds)
    for feed_url in feeds[:3]:  # Cap at 3
        try:
            log_info(f"[Pipeline] 📡 RSS: {feed_url[:50]}...")
            links = scrape_rss_links(feed_url, max_links=3)
            for link in links:
                all_links.append({"url": link, "source_type": "rss"})
        except Exception as e:
            log_info(f"[Pipeline]   ❌ {e}")
    
    return all_links


def _score_article(scraped: dict) -> int:
    """
    Score an article 0-100 based on quality signals.
    Higher score = better article = should be published first.
    """
    score = 50  # Base score
    content = scraped.get("content", "")
    title = scraped.get("title", "")
    images = scraped.get("images", [])
    
    # Length bonus (longer = more substance, up to a point)
    word_count = len(content.split())
    if word_count > 800:
        score += 15
    elif word_count > 400:
        score += 10
    elif word_count < 150:
        score -= 20  # Too short, probably garbage
    
    # Image bonus
    if len(images) >= 2:
        score += 10
    elif len(images) >= 1:
        score += 5
    
    # Title quality
    if len(title) > 20 and len(title) < 100:
        score += 5
    if any(word in title.lower() for word in ['ai', 'new', 'launch', 'release', 'update', 'breaking', 'exclusive', 'review']):
        score += 10  # Trending/newsworthy topics
    
    # Penalty for listicles and low-effort content
    if title.lower().startswith(('top ', 'best ', '10 ', '5 ', '7 ')):
        score -= 5
    
    return max(0, min(100, score))


def run_article_pipeline() -> int:
    """
    Smart publishing pipeline:
    1. Gathers links from ALL 3 categories (Sitemaps, Reddit, RSS)
    2. Scrapes and SCORES each article
    3. Publishes ONLY the highest-scoring articles
    4. Random delay between publications

    Returns: number of articles published
    """
    settings = load_dynamic_settings()
    config = load_config()
    quota_remaining = int(os.environ.get("DAILY_QUOTA_REMAINING", settings.get("daily_article_quota", 3)))

    if quota_remaining <= 0:
        log_info("[Article Pipeline] ⏸ تم استنفاد الحصة اليومية. لن يتم نشر مقالات جديدة.")
        return 0

    log_info(f"[Article Pipeline] 📊 الحصة المتبقية: {quota_remaining} مقال/مقالات")
    log_info("[Article Pipeline] 🔀 جاري جمع المقالات من الأقسام الثلاثة...")

    # Phase 1: Gather from ALL sources
    all_link_entries = _gather_all_links(settings, config)
    
    # Also include manual sources from config
    for src in config.get("sources", []):
        try:
            links = scrape_latest_links(src, max_links=2)
            for link in links:
                all_link_entries.append({"url": link, "source_type": "config"})
        except:
            pass
    
    if not all_link_entries:
        log_info("[Article Pipeline] ⚠ لم يتم العثور على أي روابط جديدة من أي مصدر.")
        return 0
    
    # Deduplicate
    seen = set()
    unique_entries = []
    for entry in all_link_entries:
        if entry["url"] not in seen:
            seen.add(entry["url"])
            unique_entries.append(entry)
    
    random.shuffle(unique_entries)
    
    # Count by source type
    source_counts = {}
    for e in unique_entries:
        source_counts[e["source_type"]] = source_counts.get(e["source_type"], 0) + 1
    log_info(f"[Article Pipeline] 📑 إجمالي الروابط: {len(unique_entries)} (Sitemaps: {source_counts.get('sitemap', 0)}, Reddit: {source_counts.get('reddit', 0)}, RSS: {source_counts.get('rss', 0)}, Config: {source_counts.get('config', 0)})")

    # Phase 2: Scrape ALL articles and score them
    log_info("[Article Pipeline] 🧠 جاري تحليل وتقييم جودة المقالات...")
    candidates = []
    
    for entry in unique_entries:
        link = entry["url"]
        
        if is_url_processed(link):
            continue
        
        try:
            scraped = scrape_article(link)
            if not scraped or scraped == "too_old" or not scraped.get("content"):
                continue
            
            score = _score_article(scraped)
            scraped["_score"] = score
            scraped["_source_type"] = entry["source_type"]
            candidates.append(scraped)
            log_info(f"[Article Pipeline]   📊 Score: {score}/100 | {scraped['title'][:50]}...")
        except Exception as e:
            log_info(f"[Article Pipeline]   ❌ فشل: {e}")
            continue
    
    if not candidates:
        log_info("[Article Pipeline] ⚠ لا توجد مقالات مؤهلة للنشر.")
        return 0
    
    # Phase 3: Sort by score (best first) and publish
    candidates.sort(key=lambda x: x.get("_score", 0), reverse=True)
    log_info(f"[Article Pipeline] 🏆 تم تقييم {len(candidates)} مقال. جاري نشر الأفضل...")
    
    published_count = 0
    for scraped in candidates:
        if published_count >= quota_remaining:
            log_info(f"[Article Pipeline] ✅ تم الوصول للحصة اليومية ({quota_remaining} مقال).")
            break
        
        score = scraped.get("_score", 0)
        if score < 30:
            log_info(f"[Article Pipeline]   ⏭ تخطي مقال ضعيف (Score: {score})")
            continue
        
        log_info(f"[Article Pipeline] 📰 نشر [{scraped.get('_source_type', '?').upper()}] Score:{score} | {scraped['title'][:50]}...")
        
        try:
            success = process_scraped_data(scraped)
            
            if success:
                published_count += 1
                log_info(f"[Article Pipeline] 🎉 نُشر بنجاح! ({published_count}/{quota_remaining})")
                
                # Randomized Publication Delay
                delay_range = settings.get("publish_delay_range", [10, 60])
                wait_mins = random.randint(delay_range[0], delay_range[1])
                log_info(f"[Article Pipeline] ⏳ انتظار {wait_mins} دقيقة قبل المقال التالي...")
                
                for _ in range(wait_mins * 60):
                    if os.environ.get("STOP_BOT"): break
                    time.sleep(1)
            else:
                log_info(f"[Article Pipeline]   ⚠ فشل النشر لهذا المقال")
        except Exception as e:
            log_info(f"[Article Pipeline]   ❌ خطأ: {e}")
            continue

    log_info(f"[Article Pipeline] ━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log_info(f"[Article Pipeline] ✅ اكتملت الدورة: تم نشر {published_count} مقال جديد")
    log_info(f"[Article Pipeline] ━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return published_count


if __name__ == "__main__":
    run_article_pipeline()
