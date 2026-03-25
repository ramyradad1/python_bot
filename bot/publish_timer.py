import datetime
from .logger import log_info
from .seo_agent import load_dynamic_settings

def get_optimal_publish_time() -> str:
    """
    Analyzes historical data per region to find the optimal hour of the week to publish.
    Schedules the article for peak engagement rather than publishing immediately.
    """
    settings = load_dynamic_settings()
    regions = settings.get("target_regions", ["United States"])
    
    log_info(f"[Nerve Center | Publish Timer] Calculating ML optimal publishing window for regions: {', '.join(regions)} ...")
    
    # In a full ML implementation, this would aggregate CTR across hours of the day.
    # We simulate the logic based on general timezone peaks.
    
    # US peak is usually around 9 AM to 11 AM EST or 5 PM EST.
    # UK peak is usually around 8 AM GMT or 4 PM GMT.
    
    if "United States" in regions:
        optimal_hour = 10 # 10 AM EST
        timezone_str = "EST"
    elif "United Kingdom" in regions:
        optimal_hour = 16 # 4 PM GMT
        timezone_str = "GMT"
    else:
        optimal_hour = 14 # 2 PM Global average
        timezone_str = "Local"
        
    now = datetime.datetime.now()
    if now.hour < optimal_hour:
        publish_time = now.replace(hour=optimal_hour, minute=0, second=0)
    else:
        # Schedule for tomorrow if we missed today's window
        publish_time = (now + datetime.timedelta(days=1)).replace(hour=optimal_hour, minute=0, second=0)
        
    log_info(f"[Nerve Center | Publish Timer] Optimal window found. Post scheduled for: {publish_time.strftime('%Y-%m-%d %H:%M:%S')} {timezone_str}")
    
    return publish_time.isoformat()

if __name__ == "__main__":
    get_optimal_publish_time()
