"""
Tools de Busca Híbrida e Persistência no RAG (`tabela_vet` / `knowledge_vectors` do Excalidraw).
Permite consultar normas nacionais e internacionais, relevo/geotecnia, tipologias e
salvar conhecimento gerado nos projetos do próprio arquiteto.
"""

import json
from typing import Optional
from agno.run import RunContext

from structura_ai.database import AsyncSessionLocal
from structura_ai.integrations.vector_store import ingest_knowledge_item, search_knowledge_hybrid
from structura_ai.models import UserMemoryDecision


async def search_engineering_rag(
    run_context: RunContext,
    query: str,
    region_country: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 4,
) -> str:
    """
    Busca na `tabela_vet` (RAG Híbrido RRF) informações sobre cálculos estruturais,
    normas nacionais (NBR 6118, NBR 6120, NBR 6123) e internacionais (Eurocode 2 UE,
    ACI 318 EUA, BSLJ Japão), relevo/geotecnia (encostas, litoral, sismo) e projetos
    anteriores do próprio arquiteto.

    Args:
        query: Consulta técnica (ex: 'limite de flecha balanço Eurocode', 'fundação em encosta montanhosa').
        region_country: Opcional ('BR', 'US', 'EU', 'JP', 'GLOBAL').
        category: Opcional ('norma_nacional', 'norma_internacional', 'calculo_estrutural', 'edificacao_tipologia', 'relevo_geotecnia', 'projeto_usuario').
        top_k: Quantidade de documentos retornados (default 4).
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")

    async with AsyncSessionLocal() as db:
        results = await search_knowledge_hybrid(
            db=db,
            query=query,
            user_id=user_id,
            region_country=region_country,
            category=category,
            top_k=top_k,
        )
        return json.dumps({"query": query, "results": results}, ensure_ascii=False)


async def save_project_knowledge_to_rag(
    run_context: RunContext,
    title: str,
    knowledge_content: str,
    region_country: str = "BR",
    category: str = "projeto_usuario",
) -> str:
    """
    Armazena conhecimento gerado, soluções adotadas ou avaliações de um projeto do arquiteto
    na `tabela_vet` (`knowledge_vectors`) e na tabela de memória (`user_memory_decisions`),
    para servir como base de conhecimento nos próximos projetos dele.

    Args:
        title: Título curto do conhecimento/solução (ex: 'Solução de balanço 4.5m em encosta no Chile').
        knowledge_content: Descrição técnica detalhada do cálculo, norma e decisão arquitetônica tomada.
        region_country: País/região do projeto ('BR', 'US', 'EU', 'JP', etc.).
        category: Categoria ('projeto_usuario', 'calculo_estrutural', 'relevo_geotecnia').
    """
    deps = (run_context.dependencies if run_context else None) or {}
    user_id = deps.get("user_id", "default_user")

    async with AsyncSessionLocal() as db:
        kv = await ingest_knowledge_item(
            db=db,
            title=title,
            content=knowledge_content,
            category=category,
            region_country=region_country,
            user_id=user_id,
            technical_metadata={"saved_from_session": run_context.session_id if run_context else None},
        )
        db.add(
            UserMemoryDecision(
                user_id=user_id,
                session_id=run_context.session_id if run_context else None,
                file_id=deps.get("active_file_id"),
                memory_type="project_learning",
                title=title,
                content=knowledge_content,
                decisions_metadata={"knowledge_vector_id": kv.id, "region_country": region_country},
            )
        )
        await db.commit()

        return json.dumps(
            {
                "status": "saved",
                "knowledge_id": kv.id,
                "user_id": user_id,
                "title": kv.title,
                "region_country": kv.region_country,
                "category": kv.category,
            },
            ensure_ascii=False,
        )
