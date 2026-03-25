import os
import random
from datetime import datetime, timezone
from dotenv import load_dotenv
from .logger import log_info
from .state import GLOBAL_STOP_EVENT
import time
import re

def sanitize_slug(raw_slug: str, title: str) -> str:
    if not raw_slug or len(raw_slug) < 5:
        raw_slug = title
    slug = raw_slug.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    slug = re.sub(r'-\d+$', '', slug)  # remove trailing numbers
    words = slug.split('-')
    if len(words) > 8:
        slug = '-'.join(words[:8])
    return slug[:60].strip('-')

from .scraper import scrape_article
from .rewriter import rewrite_article
from .uniqueness import check_uniqueness
from .image_handler import process_article_image
from .social_poster import auto_share_article, ArticleMetrics
from .supabase_client import get_supabase_client

load_dotenv()


def _get_client():
    """Lazy Supabase client getter — avoids hanging at import time."""
    try:
        return get_supabase_client()
    except Exception as e:
        log_info(f"[Publisher] ❌ فشل الاتصال بـ Supabase: {e}")
        return None


def is_url_processed(url: str) -> bool:
    client = _get_client()
    if not client: return False
    try:
        response = client.table('articles').select('sourceUrl').eq('sourceUrl', url).execute()
        return len(response.data) > 0
    except Exception:
        return False

def process_and_publish_url(url: str) -> bool:
    if GLOBAL_STOP_EVENT.is_set(): return False
    
    if is_url_processed(url):
        log_info(f"Skipping {url} as it is already in the database.")
        return False
        
    log_info(f"Starting manual pipeline for: {url}")
    scraped_data = scrape_article(url)
    if not scraped_data or scraped_data == "too_old" or not scraped_data.get('content'):
        log_info(f"Scrape failed or content empty/too old for {url}")
        return False
        
    return process_scraped_data(scraped_data)

def process_scraped_data(scraped_data: dict) -> bool:
    if GLOBAL_STOP_EVENT.is_set(): return False
    
    url = scraped_data.get("sourceUrl", "")
    log_info(f"Starting AI pipeline for: \"{scraped_data['title']}\"")

    if GLOBAL_STOP_EVENT.is_set(): return False
    # 2. AI Rewrite
    rewritten = rewrite_article(scraped_data['title'], scraped_data['content'])
    if not rewritten:
        log_info(f"Rewrite failed for {url}")
        return False
        
    log_info(f"Rewrite successful. New Title: \"{rewritten.get('title')}\"")
    
    # Save the rewritten payload to JSON buffer
    from .file_logger import log_to_json
    log_to_json("rewritten_articles.json", rewritten)

    if GLOBAL_STOP_EVENT.is_set(): return False
    # 3. Uniqueness Check
    uniqueness = check_uniqueness(scraped_data['content'], rewritten.get('content', ''))
    log_info(f"Uniqueness Score: {uniqueness.get('score', 0)}%")
    
    if not uniqueness.get('isUnique'):
        log_info(f"Article rejected. Too similar ({uniqueness.get('score', 0)}%).")
        return False

    # 4. Handle Images
    final_html = rewritten.get('content', '')
    
    # Extract the best candidate for Hero Image from scraped data
    candidate_original_url = ""
    for img in scraped_data.get('images', []):
        url = img.get('url', '').lower()
        if 'gravatar' in url or 'avatar' in url or 'logo' in url or 'icon' in url or 'data:image' in url:
            continue
        candidate_original_url = img.get('url')
        break # Only process the very first valid image found
        
    log_info("[Publisher] Synthesizing primary Hero Image for the article...")
    hero_image = process_article_image(candidate_original_url, rewritten.get('title', 'Technology Article'))

    # E-E-A-T Author Profile (dynamic from settings)
    import json as _json
    _settings_path = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")
    try:
        with open(_settings_path, "r", encoding="utf-8") as _f:
            _seo_settings = _json.load(_f)
    except Exception:
        _seo_settings = {}
    author_name = _seo_settings.get("author_name", "Ramy Radad")
    internal_linking_on = _seo_settings.get("internal_linking_enabled", True)
    
    author_bio_html = f"""
    <div class="author-bio" style="margin-top: 3rem; padding: 1.5rem; background: #f8f9fa; border-left: 4px solid #0f3460; border-radius: 8px;">
        <h3 style="margin-top: 0; color: #16213e;">About the Author: {author_name}</h3>
        <p style="margin-bottom: 0; font-size: 0.95rem; line-height: 1.6;">
            {author_name} is a Senior Systems Engineer with extensive hands-on experience in enterprise IT infrastructure. 
            He specializes in managing <strong>Office 365 environments</strong>, deploying advanced <strong>Access Points</strong> and networking solutions, 
            and integrating <strong>Smart Locks</strong> and <strong>Biometric attendance devices</strong>. 
            Through his work, he has resolved hundreds of complex technical issues for businesses worldwide.
        </p>
    </div>
    """
    final_html += author_bio_html
    
    clean_slug = sanitize_slug(rewritten.get('slug', ''), rewritten.get('title', ''))
    rewritten['slug'] = clean_slug

    # 5. Save to Database (Supabase PostgreSQL)
    try:
        publish_status = _seo_settings.get("publish_status", "published")
        
        article_document = {
            "title": rewritten.get('title'),
            "slug": clean_slug,
            "metaDescription": rewritten.get('metaDescription'),
            "content": final_html,
            "category": rewritten.get('category'),
            "tags": rewritten.get('tags', []),
            "author": author_name,
            "sourceUrl": url,
            "heroImage": hero_image,
            "views": 0,
            "status": publish_status,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "publishedAt": datetime.now(timezone.utc).isoformat() if publish_status == 'published' else None,
        }

        client = _get_client()
        if client:
            client.table('articles').insert(article_document).execute()
            log_info(f"✅ Successfully published: /articles/{rewritten.get('slug')}")
            
            # 6. Auto share
            metrics = ArticleMetrics(
                title=rewritten.get('title', ''),
                url=f"https://technify.site/articles/{rewritten.get('slug')}",
                summary=rewritten.get('metaDescription', ''),
                image_url=hero_image,
                tags=rewritten.get('tags', [])
            )
            auto_share_article(metrics)
            
            # 7. Semantic Internal Linking (conditional)
            if internal_linking_on:
                from .internal_linker import inject_internal_links
                inject_internal_links(rewritten.get('title', ''), clean_slug, rewritten.get('tags', []))
            else:
                log_info("[Publisher] Internal linking disabled via dashboard.")
            
            return True
        else:
            log_info("Supabase client not initialized. Cannot save to DB.")
            return False
            
    except Exception as e:
        log_info(f"Failed to save to database: {e}")
        return False
