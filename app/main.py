"""Main application entry point for FastAPI server"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import activity, events, health, logs, preferences, settings, stories, views
from app.core.config import settings as app_settings
from app.core.logging_config import setup_logging

# Logging yapılandırması — module import edilir edilmez çalışır.
# setup_logging, disable_existing_loggers=False ile root formatını timestamp'li yapar.
# uvicorn.access'in kendi handler'ı varsa root formatını kullanmaz, bu yüzden
# açıkça timestamp'li formatter ekliyoruz.
setup_logging()

_access_logger = logging.getLogger("uvicorn.access")
if _access_logger.handlers:
    for h in _access_logger.handlers:
        if not h.formatter or not getattr(h.formatter, '_fmt', '').startswith('['):
            h.formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)-7s %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

app = FastAPI(
    title=app_settings.PROJECT_NAME,
    description=app_settings.PROJECT_DESCRIPTION,
    version=app_settings.PROJECT_VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
app.include_router(activity.router, prefix="/api/activity", tags=["activity"])

# Include view routers
app.include_router(views.router, tags=["views"])

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}