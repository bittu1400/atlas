"""Configuration settings for Atlas loaded from environment variables and .env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Atlas runtime and database configuration."""

    model_config = SettingsConfigDict(
        env_prefix="ATLAS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Logging
    environment: str = Field(default="development", description="Runtime environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres@localhost:5432/atlas",
        description="Async SQLAlchemy database connection URL",
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg://postgres@localhost:5432/atlas",
        description="Synchronous database connection URL for migrations and CLI tools",
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")

    # Storage
    storage_root: str = Field(default="var/blobs", description="Root path for blob storage")
    snapshot_root: str = Field(
        default="var/snapshots", description="Root path for source snapshots"
    )

    # API Security & CORS
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        description="Allowed CORS origins",
    )
    api_key: str | None = Field(default=None, description="API Key for endpoint authentication")
    api_auth_enabled: bool = Field(
        default=False, description="Whether API key authentication is strictly enforced"
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings instance."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings instance (for testing and runtime overrides)."""
    get_settings.cache_clear()
