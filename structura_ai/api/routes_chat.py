"""
Rotas de Chat Copiloto, Streaming SSE e Memória do Usuário (Padrão Lembry + Excalidraw).
"""

from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from structura_ai.database import get_db
from structura_ai.models import UserMemoryDecision
from structura_ai.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    UserMemoryOut,
)
from structura_ai.workflows.chatbot.runner import run_chat_workflow
from structura_ai.workflows.chatbot.streaming import stream_chat_workflow
from structura_ai.integrations.memory import (
    episode_buffer_store,
    memcell_store,
    memscene_store,
    user_profile_store,
)
from structura_ai.workflows.memory.runner import run_memory_workflow

router = APIRouter(prefix="/api/v1/chat", tags=["Copilot Chat & Agents (Lembry Stack)"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(payload: ChatMessageRequest):
    """
    Envia uma mensagem para o Copiloto Conversacional Agno.
    O agente pode responder dúvidas técnicas, acionar os 4 sub-agentes (Validador, Busca/RAG,
    Sugestão/Paisagens, GenAI/Código) e também alterar versão (v1..vn), arquivo ativo ou estilo
    se solicitado pelo usuário no chat.
    """
    reply, suggestions, ui_mutations, active_file = await run_chat_workflow(
        message=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id,
        active_file_id=payload.active_file_id,
        region_country=payload.region_country,
        selected_format=payload.selected_format,
        force_memory_flush=payload.force_memory_flush,
    )
    return ChatMessageResponse(
        reply=reply,
        session_id=payload.session_id,
        user_id=payload.user_id,
        active_file=active_file,
        ui_mutations=ui_mutations,
        suggestions=suggestions,
    )


@router.post("/stream")
async def stream_chat_message(payload: ChatMessageRequest):
    """
    Endpoint SSE (Server-Sent Events) para streaming em tempo real da resposta do Copiloto
    e eventos `ui_mutation` (Padrão Lembry).
    """
    generator = stream_chat_workflow(
        message=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id,
        active_file_id=payload.active_file_id,
        region_country=payload.region_country,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/memory", response_model=List[UserMemoryOut])
async def get_user_memory_and_decisions(
    user_id: str = Query("default_user"),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna os registros da Tabela 1 do Excalidraw (`user_memory_decisions`):
    ID user, histórico de conversa, memória e decisões arquitetônicas/estruturais tomadas.
    """
    stmt = (
        select(UserMemoryDecision)
        .where(UserMemoryDecision.user_id == user_id)
        .order_by(UserMemoryDecision.created_at.desc())
        .limit(limit)
    )
    res = await db.execute(stmt)
    rows = list(res.scalars().all())
    return [
        UserMemoryOut(
            id=r.id,
            user_id=r.user_id,
            session_id=r.session_id,
            file_id=r.file_id,
            memory_type=r.memory_type,
            title=r.title,
            content=r.content,
            decisions_metadata=r.decisions_metadata or {},
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.get("/evermemos/{user_id}")
async def get_evermemos_user_state(
    user_id: str,
    session_id: str = Query("default_session"),
):
    """
    Retorna o estado completo da arquitetura EverMemOS (Padrão Lembry.Chatbot) para o usuário:
    UserProfile, MemScenes consolidadas, MemCells episódicas e EpisodeBuffer atual.
    """
    profile = await user_profile_store.get(user_id)
    scenes = await memscene_store.list_by_user(user_id)
    cells = await memcell_store.list_by_user(user_id, limit=25)
    unconsumed = await episode_buffer_store.get_unconsumed(user_id, session_id)
    return {
        "user_id": user_id,
        "user_profile": profile.model_dump(mode="json") if profile else None,
        "mem_scenes": [s.model_dump(mode="json") for s in scenes],
        "mem_cells": [c.model_dump(mode="json") for c in cells],
        "unconsumed_buffer": unconsumed,
    }


@router.post("/evermemos/{user_id}/flush")
async def flush_evermemos_episode(
    user_id: str,
    session_id: str = Query("default_session"),
):
    """Força o fechamento e consolidação de qualquer episódio pendente no buffer EverMemOS."""
    res = await run_memory_workflow(user_id=user_id, session_id=session_id, force_flush=True)
    return res

