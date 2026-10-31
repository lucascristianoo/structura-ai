"""
Rotas da Base Vetorial (`tabela_vet` / `knowledge_vectors` — Tabela 2 do Excalidraw).
Suporta busca híbrida RRF (normas nacionais e internacionais, cálculos, relevo e projetos do usuário)
e ingestão de novos conhecimentos gerados pelos projetos do arquiteto.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from structura_ai.database import get_db
from structura_ai.integrations.vector_store import (
    ingest_knowledge_item,
    search_knowledge_hybrid,
)
from structura_ai.integrations.goias_scraper import scrape_and_seed_goias_knowledge
from structura_ai.schemas import KnowledgeCreateRequest, KnowledgeItemOut

router = APIRouter(prefix="/api/v1/knowledge", tags=["RAG & Vector Knowledge (tabela_vet)"])


@router.get("/search", response_model=List[KnowledgeItemOut])
async def search_knowledge_endpoint(
    q: str = Query(..., description="Consulta técnica para o RAG"),
    user_id: Optional[str] = Query("default_user"),
    region_country: Optional[str] = Query(None, description="Ex: BR, US, EU, JP, GLOBAL"),
    category: Optional[str] = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Executa busca híbrida (semântica + lexical RRF) na `tabela_vet`.
    """
    results = await search_knowledge_hybrid(
        db=db,
        query=q,
        user_id=user_id,
        region_country=region_country,
        category=category,
        top_k=top_k,
    )
    return [KnowledgeItemOut(**item) for item in results]


@router.post("/ingest", response_model=KnowledgeItemOut)
async def ingest_knowledge_endpoint(
    payload: KnowledgeCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Armazena novo conhecimento na `tabela_vet` (normas, relevo ou aprendizados gerados nos projetos do arquiteto).
    """
    kv = await ingest_knowledge_item(
        db=db,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        region_country=payload.region_country,
        user_id=payload.user_id,
        technical_metadata=payload.technical_metadata,
    )
    return KnowledgeItemOut(
        id=kv.id,
        user_id=kv.user_id,
        category=kv.category,
        region_country=kv.region_country,
        title=kv.title,
        content=kv.content,
        technical_metadata=kv.technical_metadata or {},
        score=1.0,
        created_at=kv.created_at.isoformat() if kv.created_at else "",
    )


@router.post("/scrape-goias")
async def scrape_goias_endpoint(
    force_network: bool = Query(False, description="Se True, realiza HTTP scraping ao vivo das fontes públicas de Goiás além do seed curado"),
):
    """
    Executa o scraper e indexador de conhecimento técnico, geotécnico, normativo e artístico-arquitetônico
    do Estado de Goiás (BR-GO) na `tabela_vet`.
    """
    return await scrape_and_seed_goias_knowledge(force_network=force_network)

