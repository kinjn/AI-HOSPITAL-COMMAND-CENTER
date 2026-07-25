"""Application settings loaded via pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

WELCOME_MESSAGE = "Welcome to Hospital command center"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "AI Hospital Command Center"
    log_level: str = "INFO"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    api_key: str = "dev-secret-key-1234" 

    # Comma-separated list of allowed origins for the React frontend.
    cors_allow_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ALLOW_ORIGINS",
    )

    @property
    def cors_allow_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins_raw.split(",") if origin.strip()]

    database_url: str = "sqlite+aiosqlite:///./data/hospital_command_center.db"

    openai_api_key: str = ""
    llm_model: str = "llama3.2:3b"
    llm_temperature: float = 0.2
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"

    whatsapp_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()