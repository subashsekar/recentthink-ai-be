"""Low-level JWT encoding and decoding utilities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID

import jwt

from shared.config import Settings, get_settings
from shared.exceptions.auth import ExpiredTokenError, InvalidTokenError


class TokenType(StrEnum):
    """Supported JWT token types."""

    ACCESS = "access"


def create_access_token(
    *,
    user_id: UUID,
    email: str,
    role: str,
    pwd_ts: float = 0.0,
    settings: Settings | None = None,
) -> str:
    """Encode and return a signed access token for the given user claims.

    Includes standard registered claims (``iss``, ``aud``, ``iat``, ``exp``,
    ``jti``) alongside the application claims so tokens can be scoped to this
    issuer/audience and individually identified via their ``jti``.

    ``pwd_ts`` is the epoch-seconds timestamp of the user's last password
    change. It lets the server reject access tokens issued before a subsequent
    password reset/change, invalidating stale sessions.
    """
    cfg = settings or get_settings()
    now = datetime.now(tz=UTC)
    expire = now + timedelta(minutes=cfg.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "user_id": str(user_id),
        "email": email,
        "role": role,
        "pwd_ts": pwd_ts,
        "token_type": TokenType.ACCESS.value,
        "iss": cfg.jwt_issuer,
        "aud": cfg.jwt_audience,
        "iat": now,
        "exp": expire,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, cfg.secret_key, algorithm=cfg.jwt_algorithm)


def decode_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Decode and validate a JWT, returning its payload.

    Validates the signature, expiry, issuer, and audience. Any failure is
    normalised to :class:`ExpiredTokenError` or :class:`InvalidTokenError`.
    """
    cfg = settings or get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            cfg.secret_key,
            algorithms=[cfg.jwt_algorithm],
            issuer=cfg.jwt_issuer,
            audience=cfg.jwt_audience,
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Invalid token.") from exc
    return payload


def verify_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Verify a JWT and return its payload (alias for :func:`decode_token`)."""
    return decode_token(token, settings=settings)
