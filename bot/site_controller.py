"""
site_controller.py — Clean Autonomous Publishing Pipeline
3 steps only: Prepare → Publish → Post-publish
"""
import os
import threading
from dotenv import load_dotenv

load_dotenv()

from .logger import log_info
from .audit_logger import log_audit
from .seo_agent import load_dynamic_settings

# Step 1: Prepare
from .reinforcement_loop import run_reinforcement_check
from .strategy_generator import generate_novel_strategies
from .decision_engine import decide_priorities

# Step 2: Publish
from .article_pipeline import run_article_pipeline
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seo_error_bot import run_seo_bot

# Step 3: Post-publish
from .ml_engine import run_regression_analysis
from .competitor_monitor import run_competitor_monitoring
from .sitemap_generator import rebuild_and_ping_sitemaps
from .memory_bank import remember


MODULE_TIMEOUT = 60
PUBLISH_TIMEOUT = 300


class StopBotException(Exception):
    pass


def safe_run(name: str, func, *args, stop_check=None, timeout=None):
    """Run a module safely with timeout. Returns result or None on failure."""
    if stop_check and stop_check():
        raise StopBotException()

    if timeout is None:
        timeout = MODULE_TIMEOUT

    # Check if module is disabled in settings
    try:
        settings = load_dynamic_settings()
        if not settings.get("modules", {}).get(name, True):
            log_info(f"[مركز التحكم] [تخطي] {name} معطلة من لوحة التحكم.")
            return None
    except Exception:
        pass

    log_info(f"[مركز التحكم] جاري تشغيل: {name}...")

    result_holder: dict = {"result": None, "error": None, "done": False}

    def _worker():
        try:
            result_holder["result"] = func(*args)
            result_holder["done"] = True
        except Exception as e:
            result_holder["error"] = e
            result_holder["done"] = True

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if not result_holder["done"]:
        log_info(f"[مركز التحكم] انتهت المهلة: {name} ({timeout} ثانية)")
        log_audit(name, "انتهت المهلة الزمنية", "TIMEOUT")
        return None

    err = result_holder["error"]
    if isinstance(err, Exception):
        log_info(f"[مركز التحكم] فشلت: {name} — {err}")
        log_audit(name, "فشل تشغيل الوحدة", "ERROR", str(err))
        return None

    log_info(f"[مركز التحكم] نجحت: {name}")
    return result_holder["result"]


# ═══════════════════════════════════════════
#  Main Pipeline
# ═══════════════════════════════════════════

def run_site_controller_with_stop_check(stop_check=None):  # type: ignore
    """Main autonomous pipeline — 3 clean steps."""
    if stop_check is None:
        stop_check = lambda: False  # type: ignore

    log_info("=" * 50)
    log_info("[مركز التحكم] بدء دورة النشر...")
    log_info("=" * 50)

    # ──── الخطوة 1: التحضير ────
    log_info("[مركز التحكم] الخطوة 1/3: التحضير والاستراتيجيات")
    safe_run("reinforcement_loop", run_reinforcement_check, stop_check=stop_check)
    safe_run("strategy_generator", generate_novel_strategies, stop_check=stop_check)
    priorities = safe_run("decision_engine", decide_priorities, stop_check=stop_check)
    if not isinstance(priorities, list):
        priorities = []
    log_audit("التحضير", f"تم تقييم {len(priorities)} وحدة", "SUCCESS")

    # ──── الخطوة 2: النشر ────
    log_info("[مركز التحكم] الخطوة 2/3: سحب وإعادة كتابة ونشر المقالات")
    published = safe_run("article_pipeline", run_article_pipeline, stop_check=stop_check, timeout=PUBLISH_TIMEOUT)
    if isinstance(published, int) and published > 0:
        log_audit("article_pipeline", f"تم نشر {published} مقال", "SUCCESS")
    else:
        log_audit("article_pipeline", "لم يتم نشر مقالات", "SUCCESS", "quota/no-links")

    # ──── تشغيل بوت السيو والأخطاء ────
    log_info("[مركز التحكم] تشغيل بوت اكتشاف الأخطاء التقنية العالية الربح...")
    safe_run("seo_error_bot", run_seo_bot, stop_check=stop_check, timeout=PUBLISH_TIMEOUT)

    # ──── الخطوة 3: ما بعد النشر ────
    log_info("[مركز التحكم] الخطوة 3/3: تحسين وتحليل")
    new_settings = safe_run("ml_engine", run_regression_analysis, stop_check=stop_check)
    safe_run("competitor_monitor", run_competitor_monitoring, stop_check=stop_check)
    safe_run("sitemap_generator", rebuild_and_ping_sitemaps, stop_check=stop_check)

    # ──── ملخص ────
    if isinstance(new_settings, dict):
        words = new_settings.get("target_word_count", 0)
        density = new_settings.get("target_keyword_density", 0)
        remember("دورة النشر", "اكتملت بنجاح", {"words": words, "density": density})
        log_audit("Nerve Center", "اكتملت الدورة بنجاح", "SUCCESS", f"كلمات: {words}")
    else:
        log_audit("Nerve Center", "اكتملت الدورة", "SUCCESS")

    log_info("=" * 50)
    log_info("[مركز التحكم] اكتملت الدورة بنجاح!")
    log_info("=" * 50)


def run_site_controller():
    run_site_controller_with_stop_check()


if __name__ == "__main__":
    run_site_controller()
