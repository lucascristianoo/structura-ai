import uuid
from pathlib import Path
from typing import Optional

from agno.agent import Agent
from agno.run import RunContext

from structura_ai.agents.agent_loader import build_agent
from structura_ai.agents.chatbot.conversational.fan_out import sub_agente_slot
from structura_ai.agents.chatbot.genai.agent import build_genai_agent
from structura_ai.agents.chatbot.search_rag.agent import build_search_rag_agent
from structura_ai.agents.chatbot.suggester.agent import build_suggester_agent
from structura_ai.agents.chatbot.validator.agent import build_validator_agent
from structura_ai.integrations.session import get_agent_memory_db
from structura_ai.tools.code_generator_tool import generate_cad_code_tool, convert_project_format_tool
from structura_ai.tools.file_version_tools import (
    change_file_style,
    list_project_files,
    select_project_file,
    switch_file_version,
)

_CONFIG = Path(__file__).parent / "config.yaml"


async def agent_validator(run_context: RunContext, message: str) -> str:
    """
    Aciona o **Agente Validador** (valida se os cálculos estruturais fazem sentido).
    Use sempre que o usuário pedir para validar cálculos, verificar flecha/momento/flambagem
    ou checar se as dimensões atuais passam na norma.
    """
    validator = build_validator_agent(dependencies=run_context.dependencies)
    session_id = f"validator_{run_context.session_id}_{uuid.uuid4().hex[:8]}"
    async with sub_agente_slot():
        result = await validator.arun(message, session_id=session_id, dependencies=run_context.dependencies)
    return result.content or ""


async def agent_search_rag(run_context: RunContext, message: str) -> str:
    """
    Aciona o **Agente de Busca de Cálculos e Tipos de Edificações/Projetos (RAG)**.
    Use quando o usuário perguntar sobre normas nacionais (NBR) ou internacionais (Eurocode, ACI, Japão),
    condições de relevo/geotecnia (encostas, litoral/maresia, sismo), tipologias de edificações
    ou pedir para salvar/consultar conhecimento gerado em projetos anteriores.
    """
    search_agent = build_search_rag_agent(dependencies=run_context.dependencies)
    session_id = f"search_rag_{run_context.session_id}_{uuid.uuid4().hex[:8]}"
    async with sub_agente_slot():
        result = await search_agent.arun(message, session_id=session_id, dependencies=run_context.dependencies)
    return result.content or ""


async def agent_suggester(run_context: RunContext, message: str) -> str:
    """
    Aciona o **Agente de Sugestão (Diferencial)**.
    Use quando o projeto apresentar uma Dor estrutural/arquitetônica ou quando o usuário pedir
    sugestões de modificação de cálculo/estrutura acompanhadas de visuais em paisagens diferentes
    (encosta, litoral, urbano, alpino) para obter insights.
    """
    suggester = build_suggester_agent(dependencies=run_context.dependencies)
    session_id = f"suggester_{run_context.session_id}_{uuid.uuid4().hex[:8]}"
    async with sub_agente_slot():
        result = await suggester.arun(message, session_id=session_id, dependencies=run_context.dependencies)
    return result.content or ""


async def agent_genai(run_context: RunContext, message: str) -> str:
    """
    Aciona o **Agente de Gen AI para Gerar**.
    Use quando o usuário pedir geração visual ou geração de artefatos CAD/3D combinados.
    """
    genai = build_genai_agent(dependencies=run_context.dependencies)
    session_id = f"genai_{run_context.session_id}_{uuid.uuid4().hex[:8]}"
    async with sub_agente_slot():
        result = await genai.arun(message, session_id=session_id, dependencies=run_context.dependencies)
    return result.content or ""


FERRAMENTAS_COPILOTO = """* Pedido para **trocar/selecionar outro arquivo carregado** → `select_project_file` (ou `list_project_files` para listar).
* Pedido para **mudar a versão ativa no topo (`v1`, `v2`, ..., `vn`)** → `switch_file_version`.
* Pedido para **mudar o estilo visual (`formato autocad`, `formato blender`, `wireframe`, `landscape_insight`)** → `change_file_style`.
* Pedido para **gerar código ou arquivo editado na linguagem/formato do arquivo (`AutoCAD DXF/ezdxf`, `Blender bpy`, `IFC BIM`)** → `generate_cad_code_tool` (ou `agent_genai`).
* Pedido para **validar se os cálculos fazem sentido** (flecha, momentos, flambagem, conformidade) → `agent_validator`.
* Pedido sobre **normas nacionais/internacionais (Brasil, EUA, Europa, Japão), relevo/geotecnia, tipos de edificações ou salvar aprendizado no RAG** → `agent_search_rag`.
* Pedido de **sugestão de modificações estruturais para sanar uma Dor + visuais em paisagens diferentes para ter insights** → `agent_suggester`.
"""


def build_conversational_agent(dependencies: Optional[dict] = None) -> Agent:
    """
    Constrói o Agente Conversacional Principal do Structura.AI (Padrão Lembry + Tools do Excalidraw).
    """
    tools = [
        list_project_files,
        select_project_file,
        switch_file_version,
        change_file_style,
        generate_cad_code_tool,
        convert_project_format_tool,
        agent_validator,
        agent_search_rag,
        agent_suggester,
        agent_genai,
    ]

    return build_agent(
        _CONFIG,
        tools=tools,
        dependencies={
            **(dependencies or {}),
            "ferramentas": FERRAMENTAS_COPILOTO,
        },
        add_datetime_to_context=True,
        add_history_to_context=True,
        db=get_agent_memory_db(),
    )
