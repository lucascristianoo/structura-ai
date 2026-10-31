from pathlib import Path
from typing import Optional

from agno.agent import Agent
from structura_ai.agents.agent_loader import build_agent
from structura_ai.tools.physics_validation_tools import validate_structural_calculations
from structura_ai.tools.rag_knowledge_tools import search_engineering_rag

_CONFIG = Path(__file__).parent / "config.yaml"


def build_validator_agent(dependencies: Optional[dict] = None) -> Agent:
    """Constrói o Agente Validador (valida se os cálculos fazem sentido)."""
    return build_agent(
        _CONFIG,
        tools=[validate_structural_calculations, search_engineering_rag],
        dependencies=dependencies,
        add_datetime_to_context=True,
    )
