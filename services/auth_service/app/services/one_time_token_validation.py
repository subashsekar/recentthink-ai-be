"""Shared validation for one-time opaque tokens (verification, password reset)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from shared.exceptions.auth import ExpiredTokenError, InvalidTokenError, UsedTokenError
from shared.logging import get_logger

logger = get_logger(__name__)


class OneTimeTokenRecord(Protocol):
    """Minimal shape of a persisted one-time token row."""

    id: UUID
    is_used: bool
    expires_at: datetime


def validate_one_time_token(
    stored: OneTimeTokenRecord | None,
    *,
    log_context: str,
    invalid_message: str,
    used_message: str,
    expired_message: str,
) -> OneTimeTokenRecord:
    """Return ``stored`` when the token is present, unused, and not expired."""
    if stored is None:
        logger.warning("%s failed: token not found", log_context)
        raise InvalidTokenError(invalid_message)

    if stored.is_used:
        logger.warning("%s failed: token already used id=%s", log_context, stored.id)
        raise UsedTokenError(used_message)

    expires_at = stored.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(tz=UTC):
        logger.warning("%s failed: token expired id=%s", log_context, stored.id)
        raise ExpiredTokenError(expired_message)

    return stored
