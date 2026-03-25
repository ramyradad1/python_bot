import json
import os
import threading
import time
import sys
from flask import Flask, render_template, request, jsonify, Response
from datetime import datetime

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "bot", "dynamic_settings.json")
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "bot", "bot_memory.json")
AUDIT_FILE = os.path.join(os.path.dirname(__file__), "bot", "audit_log.csv")

app = Flask(__name__, template_folder="templates", static_folder="static")

# ── Global bot state ──
bot_thread = None
bot_running = False
bot_stop_requested = False

AVAILABLE_REGIONS = {
    "us": "الولايات المتحدة",
    "gb": "بريطانيا",
    "de": "ألمانيا",
    "fr": "فرنسا",
    "ca": "كندا",
    "au": "أستراليا",
    "nl": "هولندا",
    "se": "السويد",
    "es": "إسبانيا",
    "it": "إيطاليا",
    "in": "الهند",
    "br": "البرازيل",
    "jp": "اليابان",
    "kr": "كوريا الجنوبية",
    "za": "جنوب أفريقيا",
    "ie": "أيرلندا",
    "nz": "نيوزيلندا",
    "sg": "سنغافورة",
}

MODULE_LABELS = {
    "reinforcement_loop": {"name": "محرك التصحيح الذاتي", "phase": 1, "desc": "يقيّم نتائج القرارات السابقة ويصحح الأخطاء."},
    "strategy_generator": {"name": "مخترع التكتيكات", "phase": 1, "desc": "يبتكر تكتيكات سيو جديدة من ذاكرة البوت."},
    "decision_engine": {"name": "محرك اتخاذ القرار", "phase": 1, "desc": "يحدد أولويات التشغيل حسب سجل العمليات."},
    "article_pipeline": {"name": "محرك نشر المقالات", "phase": 2, "desc": "يسحب مقالات → يعيد كتابتها بالذكاء الاصطناعي → ينشرها."},
    "ml_engine": {"name": "محرك التعلم الآلي", "phase": 3, "desc": "يحلل بيانات الأداء ويحسّن إعدادات المقالات."},
    "competitor_monitor": {"name": "مراقب المنافسين", "phase": 3, "desc": "يفحص مواقع المنافسين للمحتوى الجديد."},
    "sitemap_generator": {"name": "مولد خريطة الموقع", "phase": 3, "desc": "يحدث sitemap.xml ويرسله لمحركات البحث."},
    "seo_error_bot": {"name": "بوت الأخطاء التقنية (SEO)", "phase": 2, "desc": "يصطاد مشاكل الـ IT وينشر حلولها في مقالات سيو عالية الربح."},
}

def load_settings():
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_settings(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False, default=str)

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def load_audit():
    if not os.path.exists(AUDIT_FILE):
        return []
    import csv
    with open(AUDIT_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)[-20:]  # last 20 entries


@app.route("/")
def dashboard():
    settings = load_settings()
    memory = load_memory()[-10:]
    audit = load_audit()
    return render_template(
        "dashboard.html",
        settings=settings,
        modules=MODULE_LABELS,
        regions=AVAILABLE_REGIONS,
        memory=memory,
        audit=audit,
        now=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@app.route("/api/save", methods=["POST"])
def save():
    data = request.json
    settings = load_settings()
    
    # Update scalar settings
    settings["daily_article_quota"] = int(data.get("daily_article_quota", 3))
    settings["scheduler_interval_hours"] = int(data.get("scheduler_interval_hours", 6))
    settings["target_word_count"] = int(data.get("target_word_count", 1000))
    settings["target_image_count"] = int(data.get("target_image_count", 4))
    settings["target_keyword_density"] = float(data.get("target_keyword_density", 3.0))
    
    # Update regions
    settings["target_regions"] = data.get("target_regions", ["us", "gb"])
    
    # Update module toggles
    modules = data.get("modules", {})
    for key in settings.get("modules", {}):
        if key in modules:
            settings["modules"][key] = modules[key]
    
    # Update scraping sources
    scraping = data.get("scraping_sources", {})
    if scraping:
        settings["scraping_sources"] = {
            "competitor_sitemaps": scraping.get("competitor_sitemaps", []),
            "reddit_subreddits": scraping.get("reddit_subreddits", []),
            "rss_feeds": scraping.get("rss_feeds", []),
        }
    
    # SEO Enhancements: Smart Scheduling, Author Profile, Internal Linking
    if "schedule_start_hour" in data:
        settings["schedule_start_hour"] = int(data.get("schedule_start_hour", 6))
    if "schedule_end_hour" in data:
        settings["schedule_end_hour"] = int(data.get("schedule_end_hour", 23))
    if "author_name" in data:
        settings["author_name"] = data.get("author_name", "Ramy Radad")
    if "internal_linking_enabled" in data:
        settings["internal_linking_enabled"] = bool(data.get("internal_linking_enabled", True))
    
    save_settings(settings)
    return jsonify({"status": "ok", "message": "تم حفظ الإعدادات بنجاح!"})


# ── Background Bot Execution ──

def _run_bot_background():
    """Runs the full Nerve Center pipeline in an INFINITE loop in a background thread."""
    global bot_running, bot_stop_requested
    bot_running = True
    bot_stop_requested = False
    
    from bot.logger import log_info
    from bot.site_controller import StopBotException
    
    try:
        while not bot_stop_requested:
            log_info("=" * 50)
            log_info("[مركز التحكم] بدء دورة النشر الذاتي الكاملة...")
            log_info("=" * 50)
            
            from bot.site_controller import run_site_controller_with_stop_check
            run_site_controller_with_stop_check(lambda: bot_stop_requested)
            
            log_info("=" * 50)
            log_info("[مركز التحكم] ✅ اكتملت الدورة بنجاح!")
            log_info("=" * 50)
            
            if bot_stop_requested:
                break
                
            # Sleep for the configured interval before running again
            settings = load_settings()
            interval_hours = settings.get("scheduler_interval_hours", 6)
            interval_seconds = interval_hours * 3600
            
            log_info(f"[مركز التحكم] 😴 البوت في وضع السبات... الدورة القادمة بعد {interval_hours} ساعات.")
            
            # Sleep in chunks to remain responsive to stop requests
            for _ in range(int(interval_seconds)):
                if bot_stop_requested:
                    break
                time.sleep(1)
                
    except StopBotException:
        log_info("[مركز التحكم] ⛔ تم إيقاف البوت بواسطة المستخدم.")
    except Exception as e:
        log_info(f"[مركز التحكم] ❌ خطأ عام: {e}")
    finally:
        bot_running = False
        bot_stop_requested = False


class StopBotException(Exception):
    pass


@app.route("/api/seo-enhance", methods=["POST"])
def run_seo_enhance():
    """Run standalone SEO enhancer (author bio + internal linking) in background."""
    def _seo_task():
        from bot.seo_enhancer import run_seo_enhancer
        run_seo_enhancer()
    
    seo_thread = threading.Thread(target=_seo_task, daemon=True)
    seo_thread.start()
    return jsonify({"status": "ok", "message": "🚀 جاري تشغيل محسّن السيو في الخلفية... تابع اللوجز!"})


@app.route("/api/seo-error-bot", methods=["POST"])
def run_seo_error_bot():
    """Run the standalone High-CPC IT Error Hunting Bot in background."""
    def _error_bot_task():
        from seo_error_bot import run_seo_bot
        run_seo_bot()
    
    error_bot_thread = threading.Thread(target=_error_bot_task, daemon=True)
    error_bot_thread.start()
    return jsonify({"status": "ok", "message": "🎯 بوت صيد أخطاء الـ IT اشتغل! بيبحث عن كلمات غالية في المنتديات..."})


@app.route("/api/start", methods=["POST"])
def start_bot():
    global bot_thread, bot_running
    if bot_running:
        return jsonify({"status": "error", "message": "البوت شغال بالفعل!"})
    
    bot_thread = threading.Thread(target=_run_bot_background, daemon=True)
    bot_thread.start()
    return jsonify({"status": "ok", "message": "تم تشغيل البوت!"})


@app.route("/api/stop", methods=["POST"])
def stop_bot():
    global bot_stop_requested
    if not bot_running:
        return jsonify({"status": "error", "message": "البوت مش شغال حالياً."})
    
    bot_stop_requested = True
    return jsonify({"status": "ok", "message": "جاري إيقاف البوت..."})


@app.route("/api/status")
def bot_status():
    return jsonify({"running": bot_running, "stop_requested": bot_stop_requested})


@app.route("/api/logs")
def stream_logs():
    """SSE endpoint: streams live logs to the dashboard using an absolute counter."""
    from bot.logger import get_logs

    def generate():
        last_idx = 0
        while True:
            current_logs, current_counter = get_logs()
            
            # Send initial state or all logs if starting fresh
            if last_idx == 0 and current_counter > 0:
                for log_line in current_logs:
                    yield f"data: {json.dumps({'log': log_line}, ensure_ascii=False)}\n\n"
                last_idx = current_counter
            elif current_counter > last_idx:
                new_logs_count = min(current_counter - last_idx, len(current_logs))
                new_logs = current_logs[-new_logs_count:]
                for log_line in new_logs:
                    yield f"data: {json.dumps({'log': log_line}, ensure_ascii=False)}\n\n"
                last_idx = current_counter
            
            # Also send status heartbeat
            yield f"data: {json.dumps({'status': bot_running, 'stop_requested': bot_stop_requested})}\n\n"
            time.sleep(0.5)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


if __name__ == "__main__":
    print("=" * 50)
    print("  NERVE CENTER DASHBOARD")
    print("  Open http://localhost:5050 in your browser")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
