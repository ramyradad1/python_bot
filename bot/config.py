import os
import json
from dotenv import load_dotenv
from .supabase_client import get_supabase_client

load_dotenv()

DEFAULT_CONFIG = {
    "sources": [
        "https://www.theverge.com",
        "https://techcrunch.com",
        "https://www.wired.com",
        "https://dev.to",
        "https://www.smashingmagazine.com",
        "https://stackoverflow.blog",
        "https://www.tech-wd.com",
        "https://aitnews.com"
    ],
    "max_age_hours": 24,
    "articles_per_day": 6,
    "ai_model": "Google Gemini 2.5 Flash",
    "editorial_depth": 50,
    "auto_translate": False
}

def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    try:
        client = get_supabase_client()
        if client:
            res = client.table("bot_config").select("*").eq("id", "default").execute()
            if res.data and len(res.data) > 0:
                data = res.data[0]
                config["sources"] = data.get("verticals", config["sources"])
                config["articles_per_day"] = data.get("dailyTarget", config["articles_per_day"])
                config["ai_model"] = data.get("aiModel", config["ai_model"])
                config["editorial_depth"] = data.get("editorialDepth", config["editorial_depth"])
                config["auto_translate"] = data.get("autoTranslate", config["auto_translate"])
    except Exception as e:
        print(f"Failed to load resilient config via Supabase connector: {e}")
        
    return config

def save_config(config: dict) -> bool:
    try:
        client = get_supabase_client()
        if client:
            payload = {
                "id": "default",
                "verticals": config.get("sources", []),
                "dailyTarget": config.get("articles_per_day", 6),
                "aiModel": config.get("ai_model", "Google Gemini 2.5 Flash"),
                "editorialDepth": config.get("editorial_depth", 50),
                "autoTranslate": config.get("auto_translate", False)
            }
            client.table("bot_config").upsert(payload).execute()
            return True
    except Exception as e:
        print(f"Failed to flush config directly to Supabase cloud: {e}")
    return False
