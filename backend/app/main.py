import os
import sys
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import alerts
from .api import prices
from .config import (
    ALERT_JOB_INTERVAL_HOURS,
    BASE_DIR,
    DATABASE_URL,
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
)
from .database import create_tables
from .services.alert_service import run_alert_job
from .services.mandi_service import LAST_SOURCE
from .services.sync_service import LAST_REFRESH_AT

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: create tables and start the alert scheduler."""
    create_tables()
    _start_scheduler()
    yield


app = FastAPI(title="KrishiRate", version="0.3.0", lifespan=lifespan)

app.include_router(prices.router)
app.include_router(alerts.router)

# Serve frontend assets (css, js) at /static
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Simple in-memory fixed-window rate limiter (per client IP).
# Only applied to POST endpoints to protect write/refresh/alert routes.
_rate_limits = defaultdict(list)


def _client_ip(request: Request) -> str:
    """Best-effort client IP: X-Forwarded-For first entry, else client host."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _rate_limited(client_host: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS
    timestamps = _rate_limits[client_host]
    # Drop timestamps outside the window.
    _rate_limits[client_host] = [t for t in timestamps if t > window_start]
    if len(_rate_limits[client_host]) >= RATE_LIMIT_REQUESTS:
        return True
    _rate_limits[client_host].append(now)
    return False


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.method == "POST":
        client_ip = _client_ip(request)
        if _rate_limited(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Try again later."},
            )
    response = await call_next(request)
    return response


def _start_scheduler():
    """Start the APScheduler background job that checks price alerts.

    Guarded so it does not start under pytest (test imports of main).
    Interval is configurable via ALERT_JOB_INTERVAL_HOURS.
    """
    if "pytest" in sys.modules:
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_alert_job,
        IntervalTrigger(hours=ALERT_JOB_INTERVAL_HOURS),
        id="alert_job",
        replace_existing=True,
    )
    scheduler.start()


@app.get("/", response_class=FileResponse)
def index():
    return os.path.join(FRONTEND_DIR, "index.html")


@app.get("/health")
def health():
    """Health check including last data source and last refresh time."""
    return {
        "status": "ok",
        "database": DATABASE_URL,
        "last_source": LAST_SOURCE,
        "last_refresh_at": LAST_REFRESH_AT,
    }
