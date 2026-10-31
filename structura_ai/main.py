"""
Structura.AI — Monolithic FastAPI Application Entry Point.
Serving Backend REST APIs, Deterministic Structural Physics, Google Gemini AI, and Craft UI Frontend.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse

from structura_ai.config import settings
from structura_ai.database import init_db
from structura_ai.api.routes_projects import router as projects_router
from structura_ai.api.routes_analysis import router as analysis_router
from structura_ai.api.routes_export import router as export_router
from structura_ai.api.routes_plugins import router as plugins_router
from structura_ai.api.routes_agents import router as agents_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    await init_db()
    os.makedirs("./uploads", exist_ok=True)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Structural Physics & Architectural Synthesis Bridge for Architects & Civil Engineers",
    lifespan=lifespan
)

# Static and Templates configuration
base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")

os.makedirs(static_dir, exist_ok=True)
os.makedirs(templates_dir, exist_ok=True)
uploads_dir = os.path.abspath(os.path.join(base_dir, "..", "uploads"))
os.makedirs(uploads_dir, exist_ok=True)
downloads_dir = os.path.abspath(os.path.join(base_dir, "..", "downloads", "test_samples"))
os.makedirs(downloads_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/downloads/samples", StaticFiles(directory=downloads_dir), name="samples")

templates = Jinja2Templates(directory=templates_dir)

# Include API Routers
app.include_router(projects_router)
app.include_router(analysis_router)
app.include_router(export_router)
app.include_router(plugins_router)
app.include_router(agents_router)


# =========================================================================
# SINGLE-PAGE WEB VIEWER ROUTE (CRAFT UI)
# =========================================================================

@app.get("/", response_class=HTMLResponse)
async def viewer_home_page(request: Request):
    """Single-page structural viewer, file import/export, and diagnostic chatbot."""
    return templates.TemplateResponse(
        request=request,
        name="viewer.html",
        context={
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )


@app.get("/viewer")
async def legacy_viewer_redirect():
    """Redirects legacy /viewer path to canonical single-page root '/'."""
    return RedirectResponse(url="/", status_code=307)


@app.get("/health")
async def health_check():
    """Health status check."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": bool(settings.effective_api_key),
        "db": "connected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("structura_ai.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
