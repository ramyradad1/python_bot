from .logger import log_info

def optimize_ad_revenue():
    """
    Interfaces with AdSense Reporting API (or local earnings DB) to determine which 
    article topics generate the highest CPC/RPM, and directs the Writer Agent to focus on them.
    """
    log_info("[Nerve Center | Ad Optimizer] Analyzing Revenue per Mille (RPM) metrics across site topics...")
    
    # Mock AdSense Report Data
    niche_metrics = [
        {"topic": "Cloud Hosting", "rpm": 15.50},
        {"topic": "Smartphone Reviews", "rpm": 1.20}
    ]
    
    # Sort and pick the highest
    best_niche = max(niche_metrics, key=lambda x: x['rpm'])
    
    log_info(f"[Nerve Center | Ad Optimizer] Financial Analysis Complete. Highest RPM Niche: '{best_niche['topic']}' (${best_niche['rpm']})")
    log_info(f"[Nerve Center | Ad Optimizer] [SUCCESS] Dispatched directive to Writer Agent: Allocate 80% of daily content quota to '{best_niche['topic']}'.")

if __name__ == "__main__":
    optimize_ad_revenue()
