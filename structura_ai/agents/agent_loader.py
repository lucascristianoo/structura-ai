import os
from pathlib import Path
from typing import Any, Optional, Union

import yaml
from dotenv import load_dotenv
from structura_ai.config import settings

load_dotenv()


def load_yaml_config(config_path: Path) -> dict:
    """
    Lê e parseia um config.yaml de agente (Padrão Lembry).

    Args:
        config_path: Caminho absoluto para o arquivo config.yaml

    Returns:
        Dicionário com a configuração do agente
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Config de agente não encontrado: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError(f"Arquivo de configuração vazio: {config_path}")

    return config


def build_model(model_config: Union[str, dict], tier: Optional[str] = None) -> Any:
    """
    Instancia um modelo Agno a partir da configuração do YAML.
    Por padrão usa Google Gemini (POC gratuita), suportando também AWS Bedrock e OpenAI.
    """
    # Garante que GOOGLE_API_KEY esteja exportada caso GEMINI_API_KEY tenha sido configurada
    _ = settings.effective_api_key

    if isinstance(model_config, dict):
        model_config = dict(model_config)
        tier_cfg = model_config.pop("tiers", {}).get(tier)
        if tier_cfg:
            model_config.update(tier_cfg)

    if isinstance(model_config, str):
        from agno.models.google import Gemini

        return Gemini(id=model_config)

    provider = model_config.get("provider", "google").lower()
    model_id = model_config.get("id", settings.GEMINI_MODEL or "gemini-2.5-flash")
    model_params = {k: v for k, v in model_config.items() if k not in ("provider", "id")}

    if provider == "openai":
        from agno.models.openai import OpenAIChat

        return OpenAIChat(id=model_id, **model_params)
    elif provider == "aws":
        from agno.models.aws import AwsBedrock

        return AwsBedrock(id=model_id, **model_params)
    else:
        from agno.models.google import Gemini

        return Gemini(id=model_id, **model_params)


def build_agent(
    config_path: Path,
    tools: Optional[list] = None,
    dependencies: Optional[dict] = None,
    tier: Optional[str] = None,
    **kwargs,
) -> Any:
    """
    Factory para criar qualquer agente a partir do config.yaml da sua pasta (Padrão Lembry).

    Lê o YAML, instancia o modelo e monta o Agent do Agno. As tools e os
    parâmetros dinâmicos (db, output_schema, etc.) são sempre definidos no
    agent.py via kwargs — nunca no YAML.
    """
    from agno.agent import Agent

    config = load_yaml_config(config_path)
    model = build_model(config.pop("model"), tier=tier)

    config.pop("tools", None)
    config.pop("metadata", None)

    return Agent(
        model=model,
        tools=tools or [],
        dependencies=dependencies or {},
        **config,
        **kwargs,
    )
