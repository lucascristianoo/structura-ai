from pathlib import Path
from structura_ai.agents.agent_loader import build_agent
from structura_ai.schemas_memory import ConsolidatedProfile

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def get_profiling_agent():
    return build_agent(CONFIG_PATH, output_schema=ConsolidatedProfile)
