from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    internal_api_key: str = "dev-insecure-key"
    public_backend_url: str = "http://localhost:8000"
    public_frontend_url: str = "http://localhost:3000"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    model_editor: str = "gpt-4o-mini"
    model_researcher: str = "gpt-4o-mini"
    model_booker: str = "gpt-4o-mini"
    model_host: str = "gpt-4o"
    model_engineer: str = "gpt-4o-mini"
    model_publisher: str = "gpt-4o-mini"

    elevenlabs_api_key: str | None = None
    openai_tts_voice_fallback: str = "alloy"

    firecrawl_api_key: str | None = None
    tavily_api_key: str | None = None

    db_path: str = "./data/vibecast.db"
    media_dir: str = "./public/media"

    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_public_base_url: str | None = None

    slack_webhook_url: str | None = None
    cost_alert_usd: float = 2.00

    sanity_project_id: str | None = None
    sanity_dataset: str = "production"
    sanity_api_version: str = "2024-01-01"
    sanity_read_token: str | None = None
    sanity_write_token: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
