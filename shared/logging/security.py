"""Structured security-event logging helpers.

Logs meaningful authentication and authorization events without ever
recording secrets (passwords, tokens, or credentials).
"""

from __future__ import annotations

from typing import Any

from shared.logging.logger import get_logger

logger = get_logger("security")

# Fields that must never appear in log context.
_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "current_password",
        "new_password",
        "confirm_new_password",
        "refresh_token",
        "access_token",
        "token",
        "secret",
        "secret_key",
        "authorization",
    },
)


def _sanitize_context(context: dict[str, Any]) -> dict[str, Any]:
    """Strip sensitive keys from a logging context dict."""
    return {
        key: value
        for key, value in context.items()
        if key.lower() not in _SENSITIVE_KEYS
    }


def log_security_event(event: str, **context: Any) -> None:
    """Emit a structured security event at INFO level.

    ``event`` is a stable identifier (e.g. ``login_success``,
    ``forbidden_access``).  Additional keyword arguments provide
    non-sensitive context such as ``user_id`` or ``endpoint``.
    """
    safe_context = _sanitize_context(context)
    parts = [f"event={event}"]
    for key, value in safe_context.items():
        parts.append(f"{key}={value}")
    logger.info(" | ".join(parts))
