"""
Configuração de sessão e memória para agentes e workflows Agno (Padrão Lembry).

Usa PostgresDb quando POSTGRES_URL (ou DATABASE_URL postgresql) está configurada,
com fallback automático para SqliteDb em execução local/POC sem Docker.
"""

import os
from functools import lru_cache
from typing import Any, Final

from agno.db.postgres import PostgresDb
from agno.db.sqlite import SqliteDb
from structura_ai.config import settings

AGENT_SESSION_TABLE: Final[str] = "agent_sessions"
WORKFLOW_SESSION_TABLE: Final[str] = "workflow_sessions"


def _resolve_postgres_url() -> str | None:
    """Retorna a URL PostgreSQL síncrona se configurada."""
    pg_url = (
        os.getenv("POSTGRES_URL_PGVECTOR")
        or os.getenv("POSTGRES_URL")
        or settings.POSTGRES_URL
    )
    if pg_url:
        return pg_url
    db_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL
    if db_url and "postgresql" in db_url:
        return db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return None


@lru_cache(maxsize=1)
def get_agent_memory_db() -> Any:
    """
    Retorna instância singleton do storage de sessão/memória do Agno.
    """
    pg_url = _resolve_postgres_url()
    if pg_url:
        return PostgresDb(db_url=pg_url, session_table=AGENT_SESSION_TABLE)
    return SqliteDb(db_file="./structura_agno_sessions.db", session_table=AGENT_SESSION_TABLE)


@lru_cache(maxsize=1)
def get_workflow_db() -> Any:
    """
    Retorna instância singleton do storage de workflows do Agno.
    """
    pg_url = _resolve_postgres_url()
    if pg_url:
        return PostgresDb(db_url=pg_url, session_table=WORKFLOW_SESSION_TABLE)
    return SqliteDb(db_file="./structura_agno_sessions.db", session_table=WORKFLOW_SESSION_TABLE)
