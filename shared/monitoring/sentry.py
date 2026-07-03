"""Centralised Sentry initialisation and event filtering."""

from __future__ import annotations

import logging
from typing import Any

from shared.config import Settings, get_settings

logger = logging.getLogger(__name__)

# HTTP status codes that represent expected client errors — never report to Sentry.
_IGNORED_STATUS_CODES = frozenset({400, 401, 403, 404, 422, 429})

# Domain exception types that are expected and must not be reported.
_IGNORED_EXCEPTION_TYPES: tuple[type[BaseException], ...] = ()

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "confirm_new_password",
        "refresh_token",
        "access_token",
        "token",
        "authorization",
        "secret",
        "secret_key",
        "smtp_password",
        "database_url",
    },
)


def _register_ignored_exceptions() -> tuple[type[BaseException], ...]:
    """Lazily import domain exceptions to avoid circular imports."""
    from shared.exceptions.auth import AuthError
    from shared.exceptions.base import BusinessException, ValidationException
    from shared.exceptions.repository import RepositoryError
    from slowapi.errors import RateLimitExceeded

    return (
        AuthError,
        BusinessException,
        ValidationException,
        RepositoryError,
        RateLimitExceeded,
    )


def _scrub_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive keys from a Sentry event context dict."""
    return {
        key: ("[Filtered]" if key.lower() in _SENSITIVE_KEYS else value)
        for key, value in data.items()
    }


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Filter events before they are transmitted to Sentry.

    Drops expected client/business errors and scrubs sensitive data from
    the remaining events.
    """
    global _IGNORED_EXCEPTION_TYPES
    if not _IGNORED_EXCEPTION_TYPES:
        _IGNORED_EXCEPTION_TYPES = _register_ignored_exceptions()

    exc_info = hint.get("exc_info")
    if exc_info and exc_info[1] is not None:
        if isinstance(exc_info[1], _IGNORED_EXCEPTION_TYPES):
            return None

    status_code = (
        event.get("contexts", {})
        .get("response", {})
        .get("status_code")
    )
    if status_code in _IGNORED_STATUS_CODES:
        return None

    tags = event.get("tags") or {}
    if tags.get("http.status_code") in _IGNORED_STATUS_CODES:
        return None

    if "request" in event and "headers" in event["request"]:
        headers = event["request"]["headers"]
        event["request"]["headers"] = _scrub_sensitive_data(headers)

    if "extra" in event:
        event["extra"] = _scrub_sensitive_data(event["extra"])

    return event


def init_sentry(settings: Settings | None = None) -> None:
    """Initialise the Sentry SDK when a DSN is configured.

    Safe to call multiple times; Sentry ignores duplicate initialisation.
    Does nothing when ``SENTRY_DSN`` is unset (local/test environments).
    """
    cfg = settings or get_settings()
    if not cfg.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; skipping Sentry.",
        )
        return

    sentry_sdk.init(
        dsn=cfg.sentry_dsn,
        environment=cfg.sentry_environment or cfg.environment.value,
        release=cfg.sentry_release,
        traces_sample_rate=cfg.sentry_traces_sample_rate,
        send_default_pii=False,
        before_send=before_send,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            LoggingIntegration(level=logging.ERROR, event_level=logging.ERROR),
        ],
    )
    logger.info(
        "Sentry initialised environment=%s",
        cfg.sentry_environment or cfg.environment.value,
    )
