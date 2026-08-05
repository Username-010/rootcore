"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RootCore"
    app_env: Literal["development", "production", "test"] = "development"
    app_debug: bool = False
    app_version: str = "0.1.0"
    public_base_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:5173,http://localhost:8000"
    registration_mode: Literal["open", "invite", "closed"] = "open"
    secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"

    database_url: str = (
        "postgresql+asyncpg://rootcore:rootcore@localhost:5432/rootcore"
    )

    # Self-hosted comfort default: 7 days (override via ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token_expire_minutes: int = 10080
    refresh_token_expire_days: int = 90

    media_root: str = "./data/media"
    max_upload_mb: int = 15

    plantnet_api_key: str | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "info"

    # Serve built SPA from this directory when set (production image)
    static_dir: str | None = Field(default=None)

    @field_validator("secret_key")
    @classmethod
    def warn_weak_secret(cls, value: str) -> str:
        if value.startswith("change-me"):
            # Allowed in development; production deploys must override.
            return value
        if len(value) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
