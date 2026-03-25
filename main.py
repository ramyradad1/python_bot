import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os

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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
