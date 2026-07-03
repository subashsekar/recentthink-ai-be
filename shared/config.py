"""Application configuration.

Centralised, type-safe settings loaded from environment variables (and an
optional ``.env`` file) using Pydantic ``BaseSettings``. Every microservice in
RecentThink imports its configuration from here so there is a single source of
truth for environment handling.
"""

from __future__ import annotations

import warnings
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRET_DEFAULT = "change-me-in-production"

# Absolute path to the repo-root ``.env`` so settings load identically no
# matter which directory a service or tool is launched from.
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


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
        env_file=ENV_FILE,
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

    # --- Security / Auth --------------------------------------------------
    # Signing key for JWT access tokens. Must be overridden with a strong,
    # random value in every deployed environment (enforced below).
    secret_key: str = INSECURE_SECRET_DEFAULT
    # Symmetric signing algorithm for access tokens. HS256 is suitable while a
    # single service issues and verifies tokens; switch to an asymmetric
    # algorithm (e.g. RS256) if independent services need to verify tokens
    # without sharing the secret.
    jwt_algorithm: str = "HS256"
    # Access-token lifetime. Short-lived by design; clients use refresh tokens
    # to obtain new access tokens.
    access_token_expire_minutes: int = 30
    # Refresh-token lifetime. Refresh tokens are opaque, hashed at rest, and
    # rotated on every use.
    refresh_token_expire_days: int = 7
    # Registered ``iss``/``aud`` claims embedded in and validated on every
    # access token, scoping tokens to this issuer and its intended audience.
    jwt_issuer: str = "recentthink-auth"
    jwt_audience: str = "recentthink-clients"

    # --- Rate limiting ----------------------------------------------------
    # Per-IP throttling for unauthenticated auth endpoints. Structured so a
    # future API gateway can own rate limiting instead: disable here
    # (``RATE_LIMIT_ENABLED=false``) once the gateway enforces the limits.
    rate_limit_enabled: bool = True
    rate_limit_login: str = "5/minute"
    rate_limit_register: str = "5/minute"

    # --- AI providers (configured now, used in a later phase) -------------
    openai_api_key: str | None = None
    google_api_key: str | None = None

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment."""
        return self.environment is Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        """Return ``True`` for local/test development environments."""
        return self.environment in {Environment.LOCAL, Environment.TEST}

    @model_validator(mode="after")
    def _enforce_secure_secret_key(self) -> Self:
        """Reject the insecure default secret outside local development.

        Local and test environments may keep the placeholder for convenience,
        but any deployed environment (development, staging, production) must
        provide a real ``SECRET_KEY`` — the application fails fast otherwise.
        """
        if self.secret_key != INSECURE_SECRET_DEFAULT:
            return self
        if self.is_local:
            warnings.warn(
                "SECRET_KEY is using the insecure default value; set a strong "
                "SECRET_KEY before deploying.",
                stacklevel=2,
            )
            return self
        raise ValueError(
            f"SECRET_KEY must be set to a secure value in the "
            f"'{self.environment}' environment; the insecure default is not "
            f"allowed outside local development.",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Caching avoids re-reading the environment on every call and gives the
    application a single shared configuration object.
    """
    return Settings()


settings: Settings = get_settings()
