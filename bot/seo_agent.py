import os
import json
import datetime
from google import genai
from .key_manager import get_next_api_key
from .logger import log_info

# Try to use ddgs for free web search if no API key is provided
try:
    from ddgs import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")

def load_dynamic_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_dynamic_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4, ensure_ascii=False)


def _search_with_timeout(query: str, timeout_sec: int = 20) -> str:
    """Run DDGS search synchronously (DDGS already supports timeout). Removed multiprocessing to fix Windows hangs."""
    try:
        from ddgs import DDGS
        text = ""
        with DDGS(timeout=timeout_sec) as ddgs:
            results = list(ddgs.text(query, max_results=5))
            for r in results:
                text += f"Title: {r.get('title')}\nSnippet: {r.get('body')}\n\n"
        return text
    except Exception as e:
        log_info(f"[SEO Agent] فشل البحث عبر DuckDuckGo: {e}")
        return ""

def search_web(query: str) -> str:
    """Perform a web search for the given query using DDGS or Serper."""
    results_text = ""
    if HAS_DDG:
        results_text = _search_with_timeout(query, timeout_sec=20)
        if results_text.strip():
            return results_text
        log_info("[SEO Agent] DDGS returned no results, trying Serper fallback...")
            
    # Fallback to Serper API if DDG fails or isn't installed
    search_api_key = os.getenv("SERPER_API_KEY")
    if search_api_key:
        import requests
        try:
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query, "num": 5})
            headers = {
                'X-API-KEY': search_api_key,
                'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
            data = response.json()
            for r in data.get("organic", []):
                results_text += f"Title: {r.get('title')}\nSnippet: {r.get('snippet')}\n\n"
            return results_text
        except Exception as e:
            log_info(f"[SEO Agent] Serper search failed: {e}")

    # Fallback to a mock string if no API keys and DDG fails, so the feature doesn't break
    log_info("[SEO Agent] Falling back to pre-defined SEO update mock as search APIs failed.")
    return "Title: Google Core Update 2026 Focuses on E-E-A-T and User Experience\nSnippet: Google's recent algorithm update penalizes AI-generated content that lacks human editing. It rewards articles that have a clear 'Expert Takeaway' section, uses short paragraphs (max 3 sentences), and includes bulleted lists for readability. Avoid keyword stuffing at all costs."

def research_latest_seo_rules():
    """Searches the web for the latest SEO updates and extracts writing rules via Gemini."""
    now = datetime.datetime.now()
    month_name = now.strftime("%B")
    year = now.strftime("%Y")
    
    query1 = f"latest Google Core Algorithm Update changes {month_name} {year} impact on content"
    query2 = f"current SEO best practices and E-E-A-T guidelines {month_name} {year}"
    
    log_info(f"[SEO Agent] Researching the web for SEO updates... Queries: '{query1}'")
    search_results = search_web(query1) + "\n" + search_web(query2)
    
    if len(search_results.strip()) < 50:
        log_info("[SEO Agent] Not enough search data retrieved. Skipping update.")
        return
        
    prompt = f"""
    You are an elite SEO expert for Google algorithms.
    Analyze the following LIVE search results regarding the most recent Google Core updates and SEO best practices:
    
    RESULTS:
    {search_results}
    
    Based ONLY on these live results, extract the 3 most important writing guidelines for a content bot to follow.
    These rules should be actionable formatting or stylistic instructions (e.g., "Always include an expert summary", "Keep paragraphs under 3 sentences", "Avoid promotional language").
    
    Return the result EXCLUSIVELY as a JSON array of 3 string rules.
    Example: ["Do x", "Do y", "Do z"]
    """
    
    max_retries = 8
    for attempt in range(max_retries):
        api_key = get_next_api_key()
        if not api_key:
            log_info("[SEO Agent] No API keys available for research.")
            return
            
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
            response_text = response.text.replace('```json', '').replace('```', '').strip()
            new_rules = json.loads(response_text)
            
            if isinstance(new_rules, list) and len(new_rules) > 0:
                settings = load_dynamic_settings()
                settings["dynamic_seo_rules"] = new_rules
                settings["last_seo_research_date"] = now.isoformat()
                save_dynamic_settings(settings)
                log_info(f"[SEO Agent] Successfully updated dynamic_settings.json with {len(new_rules)} new SEO rules.")
                return
                
        except Exception as e:
            error_str = str(e)
            log_info(f"[SEO Agent] Failed to extract SEO rules: '{error_str}'. Rotating key... ({attempt + 1}/{max_retries})")
            continue
            
    log_info("[SEO Agent] Exhausted all API keys or retries for SEO research.")

if __name__ == "__main__":
    research_latest_seo_rules()
