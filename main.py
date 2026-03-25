import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json

from bot.publisher import process_and_publish_url
from bot.scheduler import start_scheduler, stop_scheduler, run_scheduler_cron

from bot.config import load_config, save_config
from bot.logger import log_info, get_logs
from bot.state import GLOBAL_STOP_EVENT

app = FastAPI(title="Technify Publisher Bot API")

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

class PublishRequest(BaseModel):
    url: str

class ConfigRequest(BaseModel):
    sources: list[str]
    max_age_hours: int
    articles_per_day: int
    ai_model: str
    editorial_depth: int
    auto_translate: bool

@app.on_event("startup")
def on_startup():
    log_info("FastAPI server starting up... Auto-starting scheduler.")
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    log_info("FastAPI server shutting down...")
    stop_scheduler()

@app.get("/")
def get_dashboard():
    return FileResponse(
        os.path.join(static_path, "index.html"),
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )

@app.get("/api/status")
def get_status():
    return {"status": "running", "message": "Bot API is healthy."}

@app.get("/api/logs")
def get_logs_api():
    return {"logs": get_logs()}

@app.get("/api/config")
def get_config_api():
    return load_config()

@app.post("/api/config")
def post_config_api(config: ConfigRequest):
    if save_config(config.model_dump()):
        return {"message": "Configuration saved successfully."}
    raise HTTPException(status_code=500, detail="Failed to save configuration.")

@app.post("/api/publish")
def publish_article(request: PublishRequest, background_tasks: BackgroundTasks):
    """
    Trigger the pipeline for a specific URL manually.
    Runs in the background so the request doesn't timeout.
    """
    def task(url: str):
        GLOBAL_STOP_EVENT.clear()
        success = process_and_publish_url(url)
        log_info(f"Finished manual processing for {url}. Success: {success}")
        
    background_tasks.add_task(task, request.url)
    return {"message": f"Started processing {request.url} in the background."}

@app.post("/api/cron/start")
def api_start_cron():
    GLOBAL_STOP_EVENT.clear()
    start_scheduler()
    return {"message": "Scheduler started."}

@app.post("/api/cron/stop")
def api_stop_cron():
    GLOBAL_STOP_EVENT.set()
    stop_scheduler()
    return {"message": "Scheduler stopped and all background tasks aborted."}

@app.post("/api/cron/run-now")
def api_run_cron_now(background_tasks: BackgroundTasks):
    GLOBAL_STOP_EVENT.clear()
    background_tasks.add_task(run_scheduler_cron)
    return {"message": "Triggered cron job manually in the background."}

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "bot", "dynamic_settings.json")

class ScheduleSettingsRequest(BaseModel):
    daily_article_quota: int = 8
    schedule_start_hour: int = 6
    schedule_end_hour: int = 23
    author_name: str = "Ramy Radad"
    internal_linking_enabled: bool = True

@app.get("/api/schedule")
def get_schedule_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return {
            "daily_article_quota": settings.get("daily_article_quota", 8),
            "schedule_start_hour": settings.get("schedule_start_hour", 6),
            "schedule_end_hour": settings.get("schedule_end_hour", 23),
            "author_name": settings.get("author_name", "Ramy Radad"),
            "internal_linking_enabled": settings.get("internal_linking_enabled", True),
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/api/schedule")
def post_schedule_settings(req: ScheduleSettingsRequest):
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)
        settings["daily_article_quota"] = req.daily_article_quota
        settings["schedule_start_hour"] = req.schedule_start_hour
        settings["schedule_end_hour"] = req.schedule_end_hour
        settings["author_name"] = req.author_name
        settings["internal_linking_enabled"] = req.internal_linking_enabled
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        return {"message": "Schedule settings saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
