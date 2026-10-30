"""
Structura.AI — Monolithic FastAPI Application Entry Point.
Serving Backend REST APIs, Deterministic Structural Physics, Google Gemini AI, and Craft UI Frontend.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from structura_ai.config import settings
from structura_ai.database import init_db, get_db
from structura_ai.models import Project, AnalysisResult, RedesignVariant
from structura_ai.api.routes_projects import router as projects_router
from structura_ai.api.routes_analysis import router as analysis_router
from structura_ai.api.routes_export import router as export_router
from structura_ai.api.routes_plugins import router as plugins_router
from structura_ai.api.routes_agents import router as agents_router
from structura_ai.services.sample_projects import get_preset_list, SAMPLE_PRESETS

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
# MONOLITHIC HTML PAGE ROUTES (CRAFT UI)
# =========================================================================

@app.get("/viewer", response_class=HTMLResponse)
@app.get("/model-viewer", response_class=HTMLResponse)
async def model_viewer_page(request: Request):
    """Zero-Install Lightweight Web 3D CAD/BIM Inspector with live micro-sliders."""
    presets = get_preset_list()
    return templates.TemplateResponse(
        request=request,
        name="viewer.html",
        context={
            "presets": presets,
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )


@app.get("/council", response_class=HTMLResponse)
async def council_page(request: Request):
    """Deliberation Dashboard for User Agent, Engineer Curator, and Solow Matrix."""
    return templates.TemplateResponse(
        request=request,
        name="council.html",
        context={
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Landing and active projects dashboard."""
    stmt = (
        select(Project)
        .options(selectinload(Project.analyses))
        .order_by(desc(Project.created_at))
        .limit(12)
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()
    presets = get_preset_list()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "projects": projects,
            "presets": presets,
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )


@app.get("/analyzer", response_class=HTMLResponse)
async def analyzer_page(request: Request, preset: str = "residencia_vao_livre_critico"):
    """Interactive Real-time Structural Studio with 5 Redesign Variants."""
    presets = get_preset_list()
    current_preset = SAMPLE_PRESETS.get(preset, SAMPLE_PRESETS["residencia_vao_livre_critico"])

    return templates.TemplateResponse(
        request=request,
        name="analyzer.html",
        context={
            "presets": presets,
            "selected_preset": current_preset,
            "preset_key": preset,
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )


@app.get("/project/{project_id}", response_class=HTMLResponse)
async def view_project_page(request: Request, project_id: str, db: AsyncSession = Depends(get_db)):
    """Detailed view for a specific project with audit report and variants."""
    stmt = (
        select(Project)
        .options(
            selectinload(Project.analyses).selectinload(AnalysisResult.variants)
        )
        .where(Project.id == project_id)
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    latest_analysis = project.analyses[-1] if project.analyses else None

    return templates.TemplateResponse(
        request=request,
        name="project_view.html",
        context={
            "project": project,
            "analysis": latest_analysis,
            "app_name": settings.APP_NAME,
            "gemini_active": bool(settings.effective_api_key)
        }
    )


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
