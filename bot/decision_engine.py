import json
import os
import csv
import datetime
from .logger import log_info

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "dynamic_settings.json")
AUDIT_LOG_FILE = os.path.join(os.path.dirname(__file__), "audit_log.csv")

def check_last_run(module_name: str) -> int:
    """Check audit CSV for last successful run of a module. Returns days since last run."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return 999

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # Search from newest to oldest
        for row in reversed(rows):
            if row.get("Module") == module_name and row.get("Result") == "SUCCESS":
                date_str = row.get("Timestamp", "")
                # Handle ISO format timestamps (2026-03-24T10:00:00.123456)
                try:
                    last_run = datetime.datetime.fromisoformat(date_str)
                    delta = datetime.datetime.now() - last_run
                    return delta.days
                except ValueError:
                    continue
    except Exception:
        pass
    return 999

def decide_priorities() -> list:
    """
    AI-driven triage: determines which modules should run based on
    time elapsed since their last successful execution.
    """
    log_info("[Decision Engine] جاري تحليل سجل العمليات لتحديد الأولويات...")

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    priorities = []

    # 1. Sitemap Generator (every 1 day)
    days = check_last_run("sitemap_generator")
    if days >= 1:
        priorities.append({"module": "sitemap_generator", "reason": f"لم يتم تحديث خريطة الموقع منذ {days} يوم", "urgency": "CRITICAL"})

    # 2. Competitor Monitor (every 3 days)
    days = check_last_run("competitor_monitor")
    if days >= 3:
        priorities.append({"module": "competitor_monitor", "reason": f"لم يتم فحص المنافسين منذ {days} يوم", "urgency": "HIGH"})

    # 3. Content Refresh (every 7 days)
    days = check_last_run("content_refresh")
    if days >= 7:
        priorities.append({"module": "content_refresh", "reason": "حان موعد الفحص الأسبوعي للمحتوى القديم", "urgency": "ROUTINE"})

    # 4. Keyword Gap (every 14 days)
    days = check_last_run("keyword_gap")
    if days >= 14:
        priorities.append({"module": "keyword_gap", "reason": "حان موعد فحص فجوات الكلمات المفتاحية", "urgency": "ROUTINE"})

    # 5. Always-on priorities
    priorities.append({"module": "trend_spotter", "reason": "بحث مستمر عن التريندات", "urgency": "CRITICAL"})
    priorities.append({"module": "ml_engine", "reason": "تعلم آلي مستمر", "urgency": "ROUTINE"})

    log_info(f"[Decision Engine] تم تحديد {len(priorities)} وحدة للتشغيل اليوم")
    for p in priorities:
        log_info(f"  -> [{p['urgency']}] {p['module']}: {p['reason']}")

    # Sort by urgency
    urgency_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "ROUTINE": 3, "LOW": 4}
    priorities.sort(key=lambda x: urgency_map.get(x["urgency"], 99))

    return priorities

if __name__ == "__main__":
    decide_priorities()
