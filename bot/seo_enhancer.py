"""
Standalone SEO Enhancer — runs E-E-A-T author injection + internal linking
across ALL existing articles in Supabase, independent of the publishing pipeline.
"""
import json
import os
from .logger import log_info
from .supabase_client import get_supabase_client


SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")


def _load_seo_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _build_author_bio(author_name: str) -> str:
    return f"""
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


def run_seo_enhancer():
    """
    Scan all published articles and:
    1. Inject/update E-E-A-T author bio if missing
    2. Run internal linking across tag-matched articles
    """
    settings = _load_seo_settings()
    author_name = settings.get("author_name", "Ramy Radad")
    linking_enabled = settings.get("internal_linking_enabled", True)

    client = get_supabase_client()
    if not client:
        log_info("[SEO Enhancer] ❌ Failed to connect to Supabase.")
        return {"status": "error", "message": "Supabase connection failed"}

    log_info("=" * 50)
    log_info("[SEO Enhancer] 🚀 بدء تحسينات السيو المستقلة...")
    log_info("=" * 50)

    # ── Phase 1: E-E-A-T Author Bio Injection ──
    log_info(f"[SEO Enhancer] 👤 Phase 1: Injecting author bio for '{author_name}'...")
    
    try:
        response = client.table('articles').select('id, title, slug, content, author').order('publishedAt', desc=True).limit(200).execute()
        articles = response.data or []
    except Exception as e:
        log_info(f"[SEO Enhancer] ❌ Failed to fetch articles: {e}")
        return {"status": "error", "message": str(e)}

    bio_html = _build_author_bio(author_name)
    bio_count = 0
    link_count = 0

    for article in articles:
        content = article.get('content', '') or ''

        # Check if author bio is already present
        if 'class="author-bio"' not in content:
            updated_content = content + bio_html
            try:
                client.table('articles').update({
                    'content': updated_content,
                    'author': author_name
                }).eq('id', article['id']).execute()
                bio_count += 1
                log_info(f"[SEO Enhancer] ✅ Author bio added to: '{article.get('title', '')[:50]}'")
            except Exception as e:
                log_info(f"[SEO Enhancer] ⚠️ Failed to update article {article['id']}: {e}")
        else:
            # Update author name in DB field even if bio exists
            if article.get('author') != author_name:
                try:
                    client.table('articles').update({'author': author_name}).eq('id', article['id']).execute()
                except Exception:
                    pass

    log_info(f"[SEO Enhancer] 👤 Phase 1 complete: {bio_count} articles updated with author bio.")

    # ── Phase 2: Internal Linking ──
    if linking_enabled:
        log_info("[SEO Enhancer] 🔗 Phase 2: Running internal linking scan...")
        
        import random
        try:
            all_articles = client.table('articles').select('id, title, slug, tags').order('publishedAt', desc=True).limit(200).execute()
            all_data = all_articles.data or []
        except Exception as e:
            log_info(f"[SEO Enhancer] ❌ Failed to fetch articles for linking: {e}")
            all_data = []
        
        for article in all_data:
            tags = article.get('tags', []) or []
            if not tags:
                continue
            
            art_tags = set(t.lower() for t in tags if t)
            
            # Find related articles
            related = []
            for other in all_data:
                if other['id'] == article['id']:
                    continue
                other_tags = set(t.lower() for t in (other.get('tags', []) or []) if t)
                if art_tags.intersection(other_tags):
                    related.append(other)
            
            if not related:
                continue
                
            # Check if this article already has related links
            try:
                full_art = client.table('articles').select('id, content').eq('id', article['id']).execute()
                if not full_art.data:
                    continue
                content = full_art.data[0].get('content', '') or ''
            except Exception:
                continue
                
            if "class='related-articles'" in content or 'class="related-articles"' in content:
                continue  # Already has related links
            
            # Pick up to 3 random related
            selected = random.sample(related, min(3, len(related)))
            related_html = "<div class='related-articles' style='margin-top:2rem; padding:1.5rem; background:#fff; border:1px solid #ddd; border-radius:8px;'><h3>Related Technical Guides</h3><ul>"
            for rel in selected:
                related_html += f"<li><a href='/articles/{rel['slug']}'>{rel['title']}</a></li>"
            related_html += "</ul></div>"
            
            try:
                client.table('articles').update({
                    'content': content + related_html
                }).eq('id', article['id']).execute()
                link_count += 1
            except Exception as e:
                log_info(f"[SEO Enhancer] ⚠️ Link injection failed for {article['id']}: {e}")
        
        log_info(f"[SEO Enhancer] 🔗 Phase 2 complete: {link_count} articles got new internal links.")
    else:
        log_info("[SEO Enhancer] 🔗 Internal linking is disabled — skipped.")

    log_info("=" * 50)
    log_info(f"[SEO Enhancer] ✅ SEO Enhancement complete! Bio: {bio_count}, Links: {link_count}")
    log_info("=" * 50)
    
    return {
        "status": "ok",
        "bio_injected": bio_count,
        "links_injected": link_count,
        "total_articles": len(articles)
    }
