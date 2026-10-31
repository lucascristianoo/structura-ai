"""
Structura.AI — API Backend & Orquestrador de Agentes Agno (Padrão Lembry + Arquitetura Excalidraw).
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from structura_ai.config import settings
from structura_ai.database import AsyncSessionLocal, init_db
from structura_ai.integrations.vector_store import ensure_knowledge_seeded
from structura_ai.api.routes_files import router as files_router
from structura_ai.api.routes_chat import router as chat_router
from structura_ai.api.routes_knowledge import router as knowledge_router
from structura_ai.api.routes_projects import router as projects_router
from structura_ai.api.routes_analysis import router as analysis_router
from structura_ai.api.routes_export import router as export_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.GENERATED_DIR, exist_ok=True)
    await init_db()
    async with AsyncSessionLocal() as db:
        await ensure_knowledge_seeded(db)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend API & Agno Multi-Agent Runtime (Padrão Lembry) para Copiloto Estrutural/Arquitetônico: "
        "Versionamento por Arquivo (v1..vn), Mudança de Estilo (AutoCAD/Blender), Tool de Código e RAG Internacional."
    ),
    lifespan=lifespan,
)

# CORS liberado para o Frontend (desenvolvido separadamente) consumir REST e SSE sem bloqueios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(base_dir, "static")
templates_dir = os.path.join(base_dir, "templates")
uploads_dir = os.path.abspath(os.path.join(base_dir, "..", "uploads"))
os.makedirs(uploads_dir, exist_ok=True)
os.makedirs(os.path.join(uploads_dir, "generated"), exist_ok=True)

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

templates = Jinja2Templates(directory=templates_dir)

# Rotas principais da arquitetura Excalidraw + Lembry
app.include_router(files_router)
app.include_router(chat_router)
app.include_router(knowledge_router)

# Rotas de motor físico determinístico e exportação BIM/CAD
app.include_router(projects_router)
app.include_router(analysis_router)
app.include_router(export_router)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="viewer.html",
        context={"page_title": "Structura.AI — Copiloto Estrutural & Arquitetônico"},
    )


@app.get("/viewer")
async def viewer_redirect():
    return RedirectResponse(url="/", status_code=307)


@app.get("/api/info")
async def root_info():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "architecture": "Lembry Agno Agents + EverMemOS + Excalidraw Versioning/RAG/Code-Tool",
        "docs_url": "/docs",
        "endpoints": {
            "files_and_versions": "/api/v1/files",
            "copilot_chat": "/api/v1/chat/message",
            "copilot_stream_sse": "/api/v1/chat/stream",
            "evermemos_state": "/api/v1/chat/evermemos/{user_id}",
            "knowledge_rag": "/api/v1/knowledge/search",
            "goias_scraper": "/api/v1/knowledge/scrape-goias",
            "physics_analysis": "/api/analysis/quick-calc",
        },
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "gemini_configured": bool(settings.effective_api_key),
        "default_model": settings.GEMINI_MODEL,
        "db": "connected",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("structura_ai.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
