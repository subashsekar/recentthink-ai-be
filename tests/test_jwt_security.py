"""Unit tests for shared JWT utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from shared.config import Settings
from shared.exceptions.auth import ExpiredTokenError, InvalidTokenError
from shared.security.jwt import TokenType, create_access_token, decode_token, verify_token


@pytest.fixture
def jwt_settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
    )


def test_create_access_token_payload(jwt_settings: Settings) -> None:
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        email="user@example.com",
        role="USER",
        settings=jwt_settings,
    )

    payload = verify_token(token, settings=jwt_settings)
    assert payload["user_id"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert payload["role"] == "USER"
    assert payload["token_type"] == TokenType.ACCESS.value
    assert payload["iss"] == jwt_settings.jwt_issuer
    assert payload["aud"] == jwt_settings.jwt_audience
    assert "jti" in payload
    assert payload["pwd_ts"] == 0.0


def test_create_access_token_with_password_timestamp(jwt_settings: Settings) -> None:
    user_id = uuid4()
    changed_at = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)
    token = create_access_token(
        user_id=user_id,
        email="user@example.com",
        role="USER",
        pwd_ts=changed_at.timestamp(),
        settings=jwt_settings,
    )

    payload = verify_token(token, settings=jwt_settings)
    assert payload["pwd_ts"] == changed_at.timestamp()


def test_decode_expired_token_raises(jwt_settings: Settings) -> None:
    user_id = uuid4()
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user_id),
        "email": "user@example.com",
        "role": "USER",
        "token_type": TokenType.ACCESS.value,
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    token = jwt.encode(
        payload,
        jwt_settings.secret_key,
        algorithm=jwt_settings.jwt_algorithm,
    )

    with pytest.raises(ExpiredTokenError):
        decode_token(token, settings=jwt_settings)


def test_decode_invalid_token_raises(jwt_settings: Settings) -> None:
    with pytest.raises(InvalidTokenError):
        decode_token("invalid", settings=jwt_settings)
