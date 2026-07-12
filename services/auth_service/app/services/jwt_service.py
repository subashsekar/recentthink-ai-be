"""JWT creation and verification service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.models.enums import Role
from app.security.jwt import TokenType, create_access_token, decode_token, verify_token
from app.security.tokens import hash_token
from shared.config import Settings, get_settings
from shared.exceptions.auth import InvalidTokenError


class JWTService:
    """Encapsulates JWT access-token operations and opaque refresh-token generation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def create_access_token(
        self,
        *,
        user_id: UUID,
        email: str,
        role: Role,
        password_changed_at: datetime | None = None,
        is_verified: bool = False,
    ) -> str:
        """Create a signed JWT access token for the given user.

        ``password_changed_at`` is embedded as the ``pwd_ts`` epoch-seconds
        claim so tokens can be invalidated by a later password change.
        ``is_verified`` is embedded so other services can enforce email
        verification without an Auth round-trip.
        """
        return create_access_token(
            user_id=user_id,
            email=email,
            role=role.value,
            pwd_ts=self._password_timestamp(password_changed_at),
            is_verified=is_verified,
            settings=self._settings,
        )

    @staticmethod
    def _password_timestamp(value: datetime | None) -> float:
        """Return ``value`` as epoch seconds, or ``0`` when unset."""
        if value is None:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.timestamp()

    def generate_refresh_token(self) -> str:
        """Return a cryptographically secure opaque refresh token string.

        This is the raw value handed to the client; it is never persisted.
        Callers store :meth:`hash_refresh_token` of this value instead.
        """
        return secrets.token_urlsafe(32)

    def hash_refresh_token(self, token: str) -> str:
        """Return the digest under which a refresh token is stored/looked up."""
        return hash_token(token)

    def get_refresh_token_expiry(self) -> datetime:
        """Return the expiry timestamp for a newly issued refresh token."""
        return datetime.now(tz=UTC) + timedelta(
            days=self._settings.refresh_token_expire_days,
        )

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT access token."""
        return decode_token(token, settings=self._settings)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a JWT access token and return its payload."""
        return verify_token(token, settings=self._settings)

    def extract_user_id(self, token: str) -> UUID:
        """Decode an access token and return the embedded user id."""
        payload = self.verify_token(token)
        if payload.get("token_type") != TokenType.ACCESS.value:
            raise InvalidTokenError("Invalid token type.")
        user_id = payload.get("user_id")
        if not user_id:
            raise InvalidTokenError("Token payload is missing user_id.")
        return UUID(str(user_id))
