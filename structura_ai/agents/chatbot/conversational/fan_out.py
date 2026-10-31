"""
Controle de concorrência para fan-out de sub-agentes dentro de um turno do Chat (Padrão Lembry).
"""

import asyncio
from contextlib import asynccontextmanager
from structura_ai.config import settings

_SEMAPHORE: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _SEMAPHORE
    if _SEMAPHORE is None:
        _SEMAPHORE = asyncio.Semaphore(max(1, settings.CHAT_SUBAGENT_MAX_PARALLEL))
    return _SEMAPHORE


@asynccontextmanager
async def sub_agente_slot():
    """Adquire um slot de execução de sub-agente no event loop atual."""
    sem = _get_semaphore()
    async with sem:
        yield
