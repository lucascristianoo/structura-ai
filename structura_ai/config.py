import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Configurações centrais do Structura.AI (Arquitetura Lembry + Excalidraw).
    Suporta Google Gemini (Free Tier POC) como default, além de AWS Bedrock / OpenAI via agent_loader.
    """
    APP_NAME: str = "Structura.AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False

    # Banco de Dados Assíncrono (FastAPI ORM) e Síncrono (Agno Session / pgvector)
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./structura_ai.db",
        description="String de conexão SQLAlchemy async (postgresql+asyncpg ou sqlite+aiosqlite)"
    )
    POSTGRES_URL: str = Field(
        default="",
        description="String de conexão PostgreSQL síncrona para Agno PostgresDb e pgvector"
    )

    # Google Gemini & OpenRouter (Default gratuito para a POC)
    GEMINI_API_KEY: str = Field(default="", description="Chave da API Google Gemini")
    GOOGLE_API_KEY: str = Field(default="", description="Alias da chave Google Gemini")
    OPENROUTER_API_KEY: str = Field(default="", description="Chave da API OpenRouter (Modelos Gratuitos)")
    GEMINI_MODEL: str = Field(default="gemini-2.5-flash", description="Modelo Gemini padrão dos agentes")

    # Concorrência de Sub-Agentes (Padrão Lembry)
    CHAT_SUBAGENT_MAX_PARALLEL: int = Field(default=4, description="Máximo de sub-agentes em paralelo por turno")

    # Diretórios de Upload e Artefatos Gerados
    UPLOAD_DIR: str = "./uploads"
    GENERATED_DIR: str = "./uploads/generated"
    MAX_UPLOAD_SIZE_MB: int = 25

    HOST: str = "0.0.0.0"
    PORT: str | int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_api_key(self) -> str:
        """Retorna a chave ativa do Gemini (GEMINI_API_KEY ou GOOGLE_API_KEY)."""
        key = (
            self.GEMINI_API_KEY
            or self.GOOGLE_API_KEY
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        )
        if key and not key.startswith("STRUCTURA-FREE-") and not key.startswith("sk-or-"):
            os.environ["GOOGLE_API_KEY"] = key
            os.environ["GEMINI_API_KEY"] = key
        return key

    @property
    def is_llm_configured(self) -> bool:
        return bool(
            self.GEMINI_API_KEY
            or self.GOOGLE_API_KEY
            or self.OPENROUTER_API_KEY
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
        )


settings = Settings()
