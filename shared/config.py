"""Application configuration.

Centralised, type-safe settings loaded from environment variables (and an
optional ``.env`` file) using Pydantic ``BaseSettings``. Every microservice in
RecentThink imports its configuration from here so there is a single source of
truth for environment handling.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported deployment environments."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogLevel(StrEnum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Strongly-typed application settings sourced from the environment.

    Values are read (in order of precedence) from real environment variables
    and then from a local ``.env`` file. Unknown variables are ignored so that
    service-specific variables do not break shared loading.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core -------------------------------------------------------------
    environment: Environment = Environment.LOCAL
    log_level: LogLevel = LogLevel.INFO

    # --- Database ---------------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://recentthink:recentthink@localhost:5432/recentthink"
    )

    # --- Security / Auth (configured now, used in a later phase) ----------
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # --- AI providers (configured now, used in a later phase) -------------
    openai_api_key: str | None = None
    google_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment."""
        return self.environment is Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Caching avoids re-reading the environment on every call and gives the
    application a single shared configuration object.
    """
    return Settings()


settings: Settings = get_settings()
