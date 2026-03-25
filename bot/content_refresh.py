import json
from datetime import datetime, timezone, timedelta
from .logger import log_info
from .supabase_client import get_supabase_client
from google import genai
from .key_manager import get_next_api_key

def run_content_decay_scan():
    """
    Connects to Supabase, fetches articles older than 90 days, asks Gemini to append 
    a '2026 Update' section to the content, and UPDATES the live Supabase record.
    """
    log_info("[Nerve Center | Content Refresher] Scanning live Supabase database for traffic decay...")
    
    try:
        supabase = get_supabase_client()
        # Find articles older than 30 days as a dynamic subset 
        # (In production, this would be 90 days and cross-checked with GA4)
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        
        # We only fetch 1 article at a time to prevent API overload
        response = supabase.table("articles").select("id, title, content").lt("publishedAt", cutoff_date).limit(1).execute()
        
        if not response.data:
            log_info("[Nerve Center | Content Refresher] All historic articles are fresh. No updates required.")
            return
            
        article = response.data[0]
        log_info(f"[Nerve Center | Content Refresher] Detected decay in article: '{article['title']}'")
        log_info(f"[Nerve Center | Content Refresher] Action: Sending content to LLM to append 'Updated [2026] Section'...")
        
        max_retries = 8
        attempt = 0
        while attempt < max_retries:
            api_key = get_next_api_key()
            if not api_key:
                log_info("[Nerve Center | Content Refresher] No API key available for LLM update.")
                return
                
            try:
                client = genai.Client(api_key=api_key)
                prompt = f"""
                You are an SEO content updater.
                I have this old article titled "{article['title']}".
                
                Original Content:
                {article['content'][:1000]}...
                
                Please generate a single HTML paragraph starting with <h3>2026 Update</h3> followed by a fresh 3-sentence update about this topic.
                Output ONLY the raw HTML. Nothing else. No markdown blocks.
                """
                
                response_llm = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                append_html = response_llm.text.strip().replace('```html', '').replace('```', '')
                
                new_content = article['content'] + "\n\n" + append_html
                
                # Update live Supabase record
                new_timestamp = datetime.now(timezone.utc).isoformat()
                res = supabase.table("articles").update({"content": new_content, "publishedAt": new_timestamp}).eq("id", article["id"]).execute()
                
                log_info(f"[Nerve Center | Content Refresher] [SUCCESS] Supabase Record Updated! Appended 2026 freshness to '{article['title']}'.")
                return
                
            except Exception as e:
                error_str = str(e)
                log_info(f"[Nerve Center | Content Refresher] Failed to refresh content: '{error_str}'. Rotating key... ({attempt+1}/{max_retries})")
                attempt += 1
                continue
                
        log_info("[Nerve Center | Content Refresher] Exhausted all API keys or retries.")
        
    except Exception as e:
        log_info(f"[Nerve Center | Content Refresher] Failed to execute content decay scan: {e}")
if __name__ == "__main__":
    run_content_decay_scan()
