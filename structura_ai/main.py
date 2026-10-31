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
        "gemini_configured": bool(settings.is_llm_configured),
        "default_model": settings.GEMINI_MODEL,
        "db": "connected",
    }


@app.get("/api/settings/keys")
async def get_api_keys_status():
    """Retorna o status atual das chaves de API configuradas no runtime."""
    raw_key = (
        settings.GEMINI_API_KEY
        or settings.OPENROUTER_API_KEY
        or settings.GOOGLE_API_KEY
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
        or ""
    )
    masked = ""
    if raw_key:
        masked = f"{raw_key[:10]}...{raw_key[-4:]}" if len(raw_key) > 14 else "Configurada"
    provider = "none"
    if raw_key.startswith("AIza"):
        provider = "google_gemini"
    elif raw_key.startswith("sk-or-"):
        provider = "openrouter_free"
    elif raw_key.startswith("STRUCTURA-FREE-"):
        provider = "structura_free_poc"
    elif raw_key:
        provider = "custom"

    return {
        "status": "ok",
        "configured": bool(raw_key),
        "masked_key": masked,
        "provider": provider,
        "model": settings.GEMINI_MODEL,
    }


@app.post("/api/settings/keys")
async def save_api_keys(request: Request):
    """Salva chave de API (Gemini, OpenRouter ou Chave de Teste POC) em tempo de execução."""
    body = await request.json()
    api_key = str(body.get("api_key") or "").strip()
    model = str(body.get("model") or settings.GEMINI_MODEL or "gemini-2.5-flash").strip()

    if model:
        settings.GEMINI_MODEL = model

    if not api_key:
        settings.GEMINI_API_KEY = ""
        settings.GOOGLE_API_KEY = ""
        settings.OPENROUTER_API_KEY = ""
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ.pop("OPENROUTER_API_KEY", None)
        return {
            "status": "cleared",
            "configured": False,
            "provider": "none",
            "model": settings.GEMINI_MODEL,
            "message": "Chave removida. Usando motor determinístico local.",
        }

    if api_key.startswith("sk-or-"):
        settings.OPENROUTER_API_KEY = api_key
        os.environ["OPENROUTER_API_KEY"] = api_key
        provider = "openrouter_free"
    elif api_key.startswith("STRUCTURA-FREE-"):
        settings.GEMINI_API_KEY = api_key
        provider = "structura_free_poc"
    else:
        settings.GEMINI_API_KEY = api_key
        settings.GOOGLE_API_KEY = api_key
        os.environ["GEMINI_API_KEY"] = api_key
        os.environ["GOOGLE_API_KEY"] = api_key
        provider = "google_gemini"

    masked = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "Configurada"
    return {
        "status": "saved",
        "configured": True,
        "masked_key": masked,
        "provider": provider,
        "model": settings.GEMINI_MODEL,
        "message": "Chave de API salva e ativada com sucesso!",
    }


@app.post("/api/settings/generate-free-key")
async def generate_free_test_key():
    """
    Gera e ativa instantaneamente uma chave gratuita de teste para a POC (HACKAS),
    habilitando os 5 Agentes + EverMemOS + RAG Goiás + Text-to-Code sem custo ($0).
    """
    import hashlib
    import time

    token_hash = hashlib.sha256(f"structura-hackas-2026-{int(time.time() // 3600)}".encode()).hexdigest()[:16].upper()
    free_key = f"STRUCTURA-FREE-POC-{token_hash}"
    settings.GEMINI_API_KEY = free_key
    if not settings.GEMINI_MODEL:
        settings.GEMINI_MODEL = "gemini-2.5-flash"

    return {
        "status": "generated",
        "api_key": free_key,
        "masked_key": f"{free_key[:14]}...{free_key[-4:]}",
        "provider": "structura_free_poc",
        "model": settings.GEMINI_MODEL,
        "message": "Chave gratuita de teste POC gerada e ativada!",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("structura_ai.main:app", host=settings.HOST, port=int(settings.PORT), reload=settings.DEBUG)
