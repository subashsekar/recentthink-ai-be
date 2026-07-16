"""Tests for the shared configuration module.

These act as the project's smoke tests: they verify that settings load and that
the foundation is wired together correctly.
"""

from __future__ import annotations

from shared.config import Environment, LogLevel, Settings, get_settings


def test_settings_load_with_defaults() -> None:
    """Settings should instantiate with sensible defaults."""
    settings = Settings()

    assert isinstance(settings.environment, Environment)
    assert isinstance(settings.log_level, LogLevel)
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30


def test_get_settings_is_cached() -> None:
    """``get_settings`` must return the same cached instance."""
    assert get_settings() is get_settings()


def test_is_production_flag() -> None:
    """``is_production`` should only be true for the production environment."""
    prod = Settings(
        environment=Environment.PRODUCTION,
        secret_key="x" * 32,
        internal_service_token="secure-production-internal-token",
    )
    local = Settings(environment=Environment.LOCAL)

    assert prod.is_production is True
    assert local.is_production is False
