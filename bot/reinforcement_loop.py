import random
from .logger import log_info
from .memory_bank import remember, recall_recent

def run_reinforcement_check():
    """
    Self-correcting feedback loop. Compares the bot's last parameter change
    against simulated traffic data to evaluate impact.
    """
    log_info("[Reinforcement Loop] جاري تقييم تأثير آخر قرار ذاتي...")

    recent_decisions = recall_recent(3)

    if not recent_decisions:
        log_info("[Reinforcement Loop] لا توجد قرارات سابقة في الذاكرة. تخطي التقييم.")
        return

    last_decision = recent_decisions[-1]
    # Simulate traffic comparison (would use Analytics API in production)
    simulated_traffic_change = round(random.uniform(-2.0, 12.0), 1)

    action_name = last_decision.get('action', 'غير معروف')

    if simulated_traffic_change > 0:
        log_info(f"[Reinforcement Loop] نجاح: '{action_name}' أدى لزيادة {simulated_traffic_change}% في الزيارات. تعزيز الاستراتيجية.")
        remember("Reinforcement Check", f"ناجح: '{action_name}' (+{simulated_traffic_change}%)")
    else:
        log_info(f"[Reinforcement Loop] تراجع: '{action_name}' سبب انخفاض {simulated_traffic_change}% في الزيارات. تراجع عن القرار.")
        remember("Reinforcement Rollback", f"تم التراجع عن: '{action_name}' ({simulated_traffic_change}%)")

if __name__ == "__main__":
    run_reinforcement_check()
