import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    """
    Application Settings for Structura.AI
    Monolithic FastAPI + PostgreSQL + Google Free Tier Gemini.
    """
    APP_NAME: str = "Structura.AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database: Supports PostgreSQL (via asyncpg) or SQLite fallback for zero-friction local run
    # Format: postgresql+asyncpg://user:password@localhost:5432/structura_db
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./structura_ai.db",
        description="Database connection string (PostgreSQL asyncpg or SQLite aiosqlite)"
    )
    
    # Google AI / Gemini Settings (Free Tier: gemini-2.5-flash / gemini-1.5-flash)
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key for multimodal vision")
    GOOGLE_API_KEY: str = Field(default="", description="Alias for Google API key")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash", description="Google Gemini model name (gemini-2.0-flash / gemini-1.5-flash)")
    
    # Upload & Storage Settings
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 15
    
    # Server Host & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_api_key(self) -> str:
        """Returns the active Google Gemini API key if configured."""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

settings = Settings()
