import json
import os
import time
from datetime import datetime
from .logger import log_info
from .site_controller import run_site_controller

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")

def load_scheduler_config() -> dict:
    """Load scheduling parameters from dynamic settings."""
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)
    return {
        "interval_hours": settings.get("scheduler_interval_hours", 6),
        "daily_quota": settings.get("daily_article_quota", 3)
    }

def run_daemon():
    """
    Autonomous daemon that runs the Nerve Center on a configurable interval.
    Respects the daily_article_quota setting controlled by the user.
    Press Ctrl+C to stop.
    """
    log_info("="*60)
    log_info("[Scheduler] AUTONOMOUS DAEMON ACTIVATED")
    log_info("[Scheduler] The Nerve Center will now operate independently.")
    log_info("="*60)
    
    articles_published_today = 0
    current_day = datetime.now().date()
    
    while True:
        config = load_scheduler_config()
        interval = config["interval_hours"]
        quota = config["daily_quota"]
        
        # Reset daily counter at midnight
        today = datetime.now().date()
        if today != current_day:
            articles_published_today = 0
            current_day = today
            log_info(f"[Scheduler] New day detected ({today}). Daily article counter reset to 0.")
        
        log_info(f"[Scheduler] Cycle starting at {datetime.now().strftime('%H:%M:%S')} | Interval: {interval}h | Articles Today: {articles_published_today}/{quota}")
        
        if articles_published_today < quota:
            log_info(f"[Scheduler] Quota allows publishing. Remaining: {quota - articles_published_today} articles.")
            os.environ["DAILY_QUOTA_REMAINING"] = str(quota - articles_published_today)
        else:
            log_info(f"[Scheduler] [HOLD] Daily quota of {quota} articles reached. Skipping content generation this cycle.")
            os.environ["DAILY_QUOTA_REMAINING"] = "0"
        
        # Run the full Nerve Center pipeline
        try:
            run_site_controller()
            articles_published_today += 1
        except Exception as e:
            log_info(f"[Scheduler] [ERROR] Nerve Center cycle failed: {e}")
        
        log_info(f"[Scheduler] Cycle complete. Sleeping for {interval} hours until next activation...")
        log_info("="*60)
        
        # Sleep for the configured interval (convert hours to seconds)
        time.sleep(interval * 3600)

if __name__ == "__main__":
    run_daemon()
