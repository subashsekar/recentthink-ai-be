"""Service-to-service authentication helpers."""

from __future__ import annotations

import secrets

from shared.config import Settings, get_settings
from shared.exceptions.auth import AuthenticationException

INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token"


def verify_internal_service_token(
    token: str | None,
    *,
    settings: Settings | None = None,
) -> None:
    """Validate the internal service token from an inter-service request."""
    cfg = settings or get_settings()
    expected = cfg.internal_service_token
    if not expected:
        raise AuthenticationException("Internal service authentication is not configured.")
    if not token or not secrets.compare_digest(token, expected):
        raise AuthenticationException("Invalid internal service token.")
