from pathlib import Path
from structura_ai.agents.agent_loader import build_agent
from structura_ai.schemas_memory import ConsolidatedScene

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def get_consolidation_agent():
    return build_agent(CONFIG_PATH, output_schema=ConsolidatedScene)
