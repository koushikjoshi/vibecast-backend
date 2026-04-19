from __future__ import annotations

from functools import lru_cache

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

    public_backend_url: str = "http://localhost:8000"
    public_frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"

    jwt_secret: str = "dev-insecure-change-me-in-prod"
    session_cookie_name: str = "vibecast_session"
    session_max_age_days: int = 30
    magic_link_ttl_min: int = 30
    magic_link_dev_log: bool = True

    internal_api_key: str = "dev-insecure-key"

    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    firecrawl_api_key: str | None = None

    db_path: str = "./data/vibecast.db"
    projects_dir: str = "./data/projects"
    media_dir: str = "./data/media"

    daily_cost_cap_usd: float = 20.0
    project_cost_cap_usd: float = 15.0

    disable_live_runs: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
