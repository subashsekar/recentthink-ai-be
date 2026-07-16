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
from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

INSECURE_SECRET_DEFAULT = "change-me-in-production"
INSECURE_INTERNAL_SERVICE_TOKEN_DEFAULT = "dev-internal-service-token"

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


class EmailProvider(StrEnum):
    """Supported transactional email transports.

    ``CONSOLE`` writes messages to the application log instead of dispatching
    them and is the safe default for local development and tests. Real
    providers (e.g. ``SMTP``) are selected via ``EMAIL_PROVIDER`` per
    environment; new providers can be added without touching business logic.
    """

    CONSOLE = "console"
    SMTP = "smtp"


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
    rate_limit_account: str = "5/minute"
    # One resend every 60 seconds (slowapi ``1/minute``).
    rate_limit_resend_verification: str = "1/minute"

    # --- Super Admin seeding ----------------------------------------------
    # When all four values are set and no SUPER_ADMIN user exists yet, the
    # auth service creates the default super-admin account on startup.
    super_admin_email: str | None = None
    super_admin_password: str | None = None
    super_admin_first_name: str | None = None
    super_admin_last_name: str | None = None

    # --- Email delivery ---------------------------------------------------
    # Transport used to dispatch transactional email (verification, etc.).
    # Defaults to CONSOLE so local development and tests never reach out to an
    # external mail server; set EMAIL_PROVIDER=smtp in deployed environments.
    email_provider: EmailProvider = EmailProvider.CONSOLE
    # Envelope/branding for outgoing mail. Kept generic and overridable so the
    # sender identity is configuration, not code.
    email_from_address: str = "no-reply@recentthink.com"
    email_from_name: str = "RecentThink"
    email_support_address: str = "support@recentthink.com"
    app_name: str = "RecentThink"
    # Base URL the frontend serves to complete verification. The one-time token
    # is appended as a ``token`` query parameter.
    email_verification_url: str = "http://localhost:3000/verify-email"
    # Lifetime of a verification token before it must be reissued.
    email_verification_token_expire_hours: int = 24
    # Base URL the frontend serves to complete a password reset. The one-time
    # token is appended as a ``token`` query parameter.
    password_reset_url: str = "http://localhost:3000/reset-password"
    # Lifetime of a password reset token before it must be reissued.
    password_reset_token_expire_hours: int = 1
    # When true, ``POST /auth/change-password`` may preserve the caller's
    # current refresh session if the client supplies a valid ``refresh_token``.
    change_password_keep_current_session: bool = False

    # --- SMTP (used when EMAIL_PROVIDER=smtp) ------------------------------
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    # STARTTLS upgrade on the SMTP connection. Disable only for local relays
    # that do not support TLS.
    smtp_use_tls: bool = True
    # Socket timeout (seconds) so a stalled mail server cannot hang a request.
    smtp_timeout_seconds: int = 10

    # --- CORS ----------------------------------------------------------------
    # Comma-separated list of allowed browser origins. Wildcard ``*`` is
    # rejected — every environment must declare explicit origins.
    #
    # ``NoDecode`` disables pydantic-settings' default JSON decoding for these
    # list fields so a plain comma-separated ``.env`` value (e.g.
    # ``CORS_ORIGINS=http://localhost:3000,https://app.example.com``) is parsed
    # by the ``field_validator`` below instead of being treated as JSON.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3003",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3003",
        ],
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    cors_allow_headers: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["Authorization", "Content-Type", "X-Request-ID"],
    )

    # --- Sentry (production monitoring) ------------------------------------
    sentry_dsn: str | None = None
    sentry_environment: str | None = None
    sentry_release: str | None = None
    sentry_traces_sample_rate: float = 0.1

    # --- AI providers -----------------------------------------------------
    openai_api_key: str | None = None
    google_api_key: str | None = None
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat"
    openrouter_timeout_seconds: int = 120

    # --- File storage -----------------------------------------------------
    # Backend used for avatars and other binary uploads. Binary content is
    # never stored in PostgreSQL — only the resulting public URL is persisted.
    # Use ``local`` for development; ``supabase`` for deployed environments.
    storage_backend: str = "local"
    storage_local_path: str = "storage"
    storage_public_base_url: str = "http://localhost:8002/media"
    # Supabase Storage (used when STORAGE_BACKEND=supabase).
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "recenthink_user_profile_picture"
    # Avatar upload limits enforced by the User Service.
    avatar_max_bytes: int = 2 * 1024 * 1024  # 2 MiB
    avatar_allowed_content_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
        ],
    )

    # --- Inter-service URLs -----------------------------------------------
    usage_service_url: str = "http://localhost:8005"
    auth_service_url: str = "http://localhost:8001"
    ai_service_url: str = "http://localhost:8004"
    user_service_url: str = "http://localhost:8002"
    admin_service_url: str = "http://localhost:8003"
    # Shared secret for service-to-service calls (e.g. AI Service → Usage Service).
    internal_service_token: str = INSECURE_INTERNAL_SERVICE_TOKEN_DEFAULT

    @field_validator(
        "cors_origins",
        "cors_allow_methods",
        "cors_allow_headers",
        "avatar_allowed_content_types",
        mode="before",
    )
    @classmethod
    def _parse_csv_list(cls, value: object) -> list[str]:
        """Accept a comma-separated string or a list of values."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @model_validator(mode="after")
    def _reject_wildcard_cors(self) -> Self:
        """Disallow wildcard CORS origins in every environment."""
        if "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS must not contain '*'; declare explicit origins.",
            )
        return self

    @property
    def is_production(self) -> bool:
        """Return ``True`` when running in the production environment."""
        return self.environment is Environment.PRODUCTION

    @property
    def is_local(self) -> bool:
        """Return ``True`` for local/test development environments."""
        return self.environment in {Environment.LOCAL, Environment.TEST}

    @model_validator(mode="after")
    def _enforce_secure_internal_service_token(self) -> Self:
        """Reject the insecure internal token default outside local development."""
        if self.internal_service_token != INSECURE_INTERNAL_SERVICE_TOKEN_DEFAULT:
            return self
        if self.is_local:
            warnings.warn(
                "INTERNAL_SERVICE_TOKEN is using the insecure default value; set a "
                "strong INTERNAL_SERVICE_TOKEN before deploying.",
                stacklevel=2,
            )
            return self
        raise ValueError(
            f"INTERNAL_SERVICE_TOKEN must be set to a secure value in the "
            f"'{self.environment}' environment; the insecure default is not "
            f"allowed outside local development.",
        )

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

    @model_validator(mode="after")
    def _validate_smtp_configuration(self) -> Self:
        """Ensure SMTP delivery is fully configured when selected.

        Fails fast at startup rather than surfacing a delivery error on the
        first verification email if ``EMAIL_PROVIDER=smtp`` but the host is
        missing.
        """
        if self.email_provider is EmailProvider.SMTP and not self.smtp_host:
            raise ValueError(
                "SMTP_HOST must be set when EMAIL_PROVIDER is 'smtp'.",
            )
        return self

    @model_validator(mode="after")
    def _configure_supabase_storage(self) -> Self:
        """Validate Supabase storage settings and derive the public base URL."""
        if self.storage_backend.strip().lower() != "supabase":
            return self
        if not self.supabase_url:
            raise ValueError(
                "SUPABASE_URL must be set when STORAGE_BACKEND is 'supabase'.",
            )
        if not self.supabase_service_role_key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY must be set when STORAGE_BACKEND is "
                "'supabase'.",
            )
        derived = (
            f"{self.supabase_url.rstrip('/')}/storage/v1/object/public/"
            f"{self.supabase_storage_bucket}"
        )
        # Replace the local-dev default so avatar delete/prefix matching works.
        if self.storage_public_base_url in {
            "http://localhost:8002/media",
            "",
        }:
            self.storage_public_base_url = derived
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached :class:`Settings` instance.

    Caching avoids re-reading the environment on every call and gives the
    application a single shared configuration object.
    """
    return Settings()


settings: Settings = get_settings()
