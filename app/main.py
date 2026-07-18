"""Main application entry point for FastAPI server"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import ai_activity, events, health, preferences, settings, stories, views
from app.core.config import settings as app_settings

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
app.include_router(stories.router, prefix="/api/stories", tags=["stories"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
app.include_router(ai_activity.router, prefix="/api/ai-activity", tags=["ai-activity"])

# Include view routers
app.include_router(views.router, tags=["views"])

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
async def simple_health_check():
    """Simple health check endpoint"""
    return {"status": "healthy"}
