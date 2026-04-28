from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Codebase Intelligence Assistant API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True
    app_log_level: str = "INFO"
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    api_v1_prefix: str = "/api/v1"
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_intelligence"
    )
    storage_root: Path = Path("./data")
    max_upload_size_mb: int = 250

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def repositories_root(self) -> Path:
        return self.storage_root / "repositories"


@lru_cache
def get_settings() -> Settings:
    return Settings()
