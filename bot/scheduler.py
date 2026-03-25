import json
import os
import time
import random
import threading
from datetime import datetime, date, timedelta
from .logger import log_info
from .site_controller import run_site_controller
from .state import GLOBAL_STOP_EVENT

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")
_scheduler_thread = None

def load_scheduler_config() -> dict:
    """Load scheduling parameters from dynamic settings."""
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)
    return {
        "daily_quota": settings.get("daily_article_quota", 8),
        "start_hour": settings.get("schedule_start_hour", 6),
        "end_hour": settings.get("schedule_end_hour", 23),
        "jitter_mins": settings.get("publish_delay_range", [10, 60])
    }

def generate_daily_schedule(quota: int, start_hour: int, end_hour: int) -> list[datetime]:
    # Generate random times between start_hour and end_hour
    now = datetime.now()
    start_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    end_time = now.replace(hour=end_hour, minute=59, second=59, microsecond=0)
    
    # If end_time is before start_time (e.g., end=2, start=6), assume end is the next day
    if end_time < start_time:
        end_time += timedelta(days=1)
        
    total_seconds = int((end_time - start_time).total_seconds())
    
    # We want to schedule 'quota' articles randomly throughout the period
    offsets = sorted([random.randint(0, total_seconds) for _ in range(quota)])
    
    schedule = [start_time + timedelta(seconds=off) for off in offsets]
    return schedule

def run_scheduler_cron():
    """Manual trigger wrapper."""
    try:
        run_site_controller()
    except Exception as e:
        log_info(f"[Scheduler] Manual trigger failed: {e}")

def daemon_loop():
    log_info("="*60)
    log_info("[Scheduler] AUTONOMOUS DAEMON ACTIVATED (Smart Scheduling)")
    log_info("="*60)
    
    current_day = None
    daily_schedule = []
    
    while not GLOBAL_STOP_EVENT.is_set():
        today = datetime.now().date()
        
        # New day reset
        if today != current_day:
            try:
                config = load_scheduler_config()
                # Randomize quota between 6 and max quota (e.g., 8)
                max_quota = config["daily_quota"]
                actual_quota = random.randint(min(6, max_quota), max_quota)
                
                daily_schedule = generate_daily_schedule(actual_quota, config["start_hour"], config["end_hour"])
                
                # Filter out times that have already passed today
                now = datetime.now()
                daily_schedule = [t for t in daily_schedule if t >= now]
                    
                current_day = today
                log_info(f"[Scheduler] New day ({today}). Generated {len(daily_schedule)} publish slots.")
                for i, t in enumerate(daily_schedule, 1):
                    log_info(f"  [{i}/{len(daily_schedule)}] Scheduled for: {t.strftime('%H:%M:%S')}")
            except Exception as e:
                log_info(f"[Scheduler] Failed to generate schedule: {e}")
                time.sleep(60)
                continue
                
        if not daily_schedule:
            # Done for today, sleep until tomorrow
            log_info("[Scheduler] All scheduled articles completed for today. Sleeping until tomorrow.")
            # Calculate seconds until midnight
            now = datetime.now()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=1, second=0, microsecond=0)
            sleep_secs = (tomorrow - now).total_seconds()
            
            # Sleep in chunks to allow stopping
            for _ in range(int(sleep_secs)):
                if GLOBAL_STOP_EVENT.is_set(): return
                time.sleep(1)
            continue
            
        next_run = daily_schedule[0]
        now = datetime.now()
        
        if now >= next_run:
            daily_schedule.pop(0)
            log_info(f"[Scheduler] Scheduled time reached! Remaining today: {len(daily_schedule)}")
            
            # Jitter
            config = load_scheduler_config()
            jitter_range = config["jitter_mins"]
            jitter = random.randint(jitter_range[0], jitter_range[1]) * 60
            log_info(f"[Scheduler] Applying jitter: waiting {jitter // 60} minutes before executing.")
            
            for _ in range(jitter):
                if GLOBAL_STOP_EVENT.is_set(): return
                time.sleep(1)
                
            try:
                os.environ["DAILY_QUOTA_REMAINING"] = str(len(daily_schedule) + 1)
                run_site_controller()
            except Exception as e:
                log_info(f"[Scheduler] [ERROR] Nerve Center cycle failed: {e}")
                
            log_info(f"[Scheduler] Cycle complete. Next article scheduled at: {daily_schedule[0].strftime('%H:%M:%S') if daily_schedule else 'Tomorrow'}")
            log_info("="*60)
        else:
            # Sleep until the next run time, checking stop event every second
            sleep_secs = (next_run - now).total_seconds()
            sleep_secs = min(sleep_secs, 60) # Wake up every minute to re-evaluate or check logs
            for _ in range(int(sleep_secs)):
                if GLOBAL_STOP_EVENT.is_set(): return
                time.sleep(1)

def start_scheduler():
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        log_info("[Scheduler] Scheduler is already running.")
        return
        
    GLOBAL_STOP_EVENT.clear()
    _scheduler_thread = threading.Thread(target=daemon_loop, daemon=True)
    _scheduler_thread.start()
    log_info("[Scheduler] Thread started.")

def stop_scheduler():
    GLOBAL_STOP_EVENT.set()
    log_info("[Scheduler] Stopping signal sent.")
    
if __name__ == "__main__":
    start_scheduler()
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            stop_scheduler()
            break
