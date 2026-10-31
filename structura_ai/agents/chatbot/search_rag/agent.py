from pathlib import Path
from typing import Optional

from agno.agent import Agent
from structura_ai.agents.agent_loader import build_agent
from structura_ai.tools.rag_knowledge_tools import (
    save_project_knowledge_to_rag,
    search_engineering_rag,
)

_CONFIG = Path(__file__).parent / "config.yaml"


def build_search_rag_agent(dependencies: Optional[dict] = None) -> Agent:
    """Constrói o Agente de Busca de Cálculos e Tipo de Edificações/Projetos conectado ao RAG."""
    return build_agent(
        _CONFIG,
        tools=[search_engineering_rag, save_project_knowledge_to_rag],
        dependencies=dependencies,
        add_datetime_to_context=True,
    )
