import random
import re
from .logger import log_info
from .supabase_client import get_supabase_client

def inject_internal_links(new_article_title: str, new_article_slug: str, tags: list):
    """
    Finds older, high-authority articles in the database that share tags with the newly published article 
    and autonomously edits their HTML to inject a semantic backlink.
    It also adds links to those older articles at the end of the new article.
    """
    if not tags:
        log_info("[Internal Linker] No tags provided for semantic linking.")
        return

    log_info(f"[Internal Linker] Semantic scan initiated for: '{new_article_title}'")
    
    client = get_supabase_client()
    if not client:
        log_info("[Internal Linker] Failed to connect to Supabase.")
        return

    try:
        # Get up to 50 recent articles to search for matching tags
        response = client.table('articles').select('id, title, slug, content, tags').neq('slug', new_article_slug).order('publishedAt', desc=True).limit(50).execute()
        
        candidates = []
        for article in response.data:
            article_tags = set(t.lower() for t in article.get('tags', []) if t)
            new_tags = set(t.lower() for t in tags if t)
            if article_tags.intersection(new_tags):
                candidates.append(article)
                
        if not candidates:
            log_info("[Internal Linker] No related articles found.")
            return
            
        # Pick up to 3 random related articles
        selected_articles = random.sample(candidates, min(3, len(candidates)))
        log_info(f"[Internal Linker] Found {len(candidates)} related articles. Selected {len(selected_articles)} for linking.")
        
        # 1. Inject links to the old articles INTO the NEW article
        # We need to update the new article we just published.
        related_html = "<div class='related-articles' style='margin-top:2rem; padding:1.5rem; background:#fff; border:1px solid #ddd; border-radius:8px;'><h3>Related Technical Guides</h3><ul>"
        for old_art in selected_articles:
            related_html += f"<li><a href='/articles/{old_art['slug']}'>{old_art['title']}</a></li>"
        related_html += "</ul></div>"
        
        # Append to new article
        new_art_res = client.table('articles').select('id, content').eq('slug', new_article_slug).execute()
        if new_art_res.data:
            new_id = new_art_res.data[0]['id']
            new_content = new_art_res.data[0]['content'] + related_html
            client.table('articles').update({'content': new_content}).eq('id', new_id).execute()
            log_info(f"[Internal Linker] Appended {len(selected_articles)} related links to '{new_article_title}'.")
            
        # 2. Inject backlink to the NEW article INTO the OLD articles
        for old_art in selected_articles:
            old_content = old_art.get('content', '')
            # Simple injection: append a "Latest Update" note at the end of the old article
            backlink_html = f"<div class='latest-update' style='margin-top:2rem; padding:1rem; background:#eef2ff; border-left:4px solid #0f3460;'><strong>Related Guide:</strong> <a href='/articles/{new_article_slug}'>{new_article_title}</a></div>"
            updated_content = old_content + backlink_html
            client.table('articles').update({'content': updated_content}).eq('id', old_art['id']).execute()
            log_info(f"[Internal Linker] Injected backlink into older article: '{old_art['title']}'")

    except Exception as e:
        log_info(f"[Internal Linker] Error during internal linking: {e}")

if __name__ == "__main__":
    inject_internal_links("How to Build Machine Learning Bots", "ml-bots-guide", ["AI", "Bot", "Machine Learning"])
