from pathlib import Path
from typing import Optional

from agno.agent import Agent
from structura_ai.agents.agent_loader import build_agent
from structura_ai.tools.code_generator_tool import generate_cad_code_tool, convert_project_format_tool
from structura_ai.tools.genai_visual_tools import generate_architectural_visual

_CONFIG = Path(__file__).parent / "config.yaml"


def build_genai_agent(dependencies: Optional[dict] = None) -> Agent:
    """Constrói o Agente de Gen AI para Text-to-Code, Conversão entre Formatos e Geração Visual."""
    return build_agent(
        _CONFIG,
        tools=[generate_cad_code_tool, convert_project_format_tool, generate_architectural_visual],
        dependencies=dependencies,
        add_datetime_to_context=True,
    )
