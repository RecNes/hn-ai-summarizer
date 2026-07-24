"""Frontend views routes."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

router = APIRouter()

# Standalone Jinja2 environment with cache disabled
# (Python 3.14+ LRUCache bug: unhashable type 'dict')
_env = Environment(loader=FileSystemLoader("app/templates"), auto_reload=True, autoescape=True)


async def _render(name: str, request: Request, **context) -> HTMLResponse:
    """Render template with Jinja2 directly (bypasses starlette's cache)."""
    template = _env.get_template(name)
    html = template.render(request=request, **context)
    return HTMLResponse(content=html)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page showing stories"""
    return await _render("index.html", request)


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return await _render("settings.html", request)


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Activity logs page"""
    return await _render("logs.html", request)