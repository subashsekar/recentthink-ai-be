"""Unit tests for JWTService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.models.enums import Role
from app.services.jwt_service import JWTService
from shared.config import Settings
from shared.exceptions.auth import ExpiredTokenError, InvalidTokenError


@pytest.fixture
def jwt_settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        jwt_algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7,
    )


@pytest.fixture
def jwt_service(jwt_settings: Settings) -> JWTService:
    return JWTService(settings=jwt_settings)


def test_create_and_verify_access_token(jwt_service: JWTService) -> None:
    user_id = uuid4()
    token = jwt_service.create_access_token(
        user_id=user_id,
        email="user@example.com",
        role=Role.USER,
    )

    payload = jwt_service.verify_token(token)
    assert payload["user_id"] == str(user_id)
    assert payload["email"] == "user@example.com"
    assert payload["role"] == Role.USER.value
    assert payload["token_type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload
    assert payload["iss"] == "recentthink-auth"
    assert payload["aud"] == "recentthink-clients"


def test_each_token_has_unique_jti(jwt_service: JWTService) -> None:
    user_id = uuid4()
    first = jwt_service.verify_token(
        jwt_service.create_access_token(
            user_id=user_id, email="user@example.com", role=Role.USER
        )
    )
    second = jwt_service.verify_token(
        jwt_service.create_access_token(
            user_id=user_id, email="user@example.com", role=Role.USER
        )
    )
    assert first["jti"] != second["jti"]


def test_wrong_issuer_rejected() -> None:
    issuer_settings = Settings(
        secret_key="x" * 32,
        jwt_algorithm="HS256",
        jwt_issuer="attacker",
        jwt_audience="recentthink-clients",
    )
    token = JWTService(settings=issuer_settings).create_access_token(
        user_id=uuid4(), email="user@example.com", role=Role.USER
    )

    verifier = JWTService(
        settings=Settings(
            secret_key="x" * 32,
            jwt_algorithm="HS256",
            jwt_issuer="recentthink-auth",
            jwt_audience="recentthink-clients",
        )
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify_token(token)


def test_wrong_audience_rejected() -> None:
    aud_settings = Settings(
        secret_key="x" * 32,
        jwt_algorithm="HS256",
        jwt_issuer="recentthink-auth",
        jwt_audience="someone-else",
    )
    token = JWTService(settings=aud_settings).create_access_token(
        user_id=uuid4(), email="user@example.com", role=Role.USER
    )

    verifier = JWTService(
        settings=Settings(
            secret_key="x" * 32,
            jwt_algorithm="HS256",
            jwt_issuer="recentthink-auth",
            jwt_audience="recentthink-clients",
        )
    )
    with pytest.raises(InvalidTokenError):
        verifier.verify_token(token)


def test_hash_refresh_token_is_deterministic_and_not_raw(
    jwt_service: JWTService,
) -> None:
    raw = jwt_service.generate_refresh_token()
    hashed = jwt_service.hash_refresh_token(raw)

    assert hashed != raw
    assert hashed == jwt_service.hash_refresh_token(raw)
    assert len(hashed) == 64  # SHA-256 hex digest


def test_extract_user_id(jwt_service: JWTService) -> None:
    user_id = uuid4()
    token = jwt_service.create_access_token(
        user_id=user_id,
        email="user@example.com",
        role=Role.USER,
    )

    assert jwt_service.extract_user_id(token) == user_id


def test_expired_token_raises(jwt_settings: Settings) -> None:
    service = JWTService(settings=jwt_settings)
    user_id = uuid4()
    now = datetime.now(tz=UTC)
    payload = {
        "user_id": str(user_id),
        "email": "user@example.com",
        "role": Role.USER.value,
        "token_type": "access",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired = jwt.encode(
        payload,
        jwt_settings.secret_key,
        algorithm=jwt_settings.jwt_algorithm,
    )

    with pytest.raises(ExpiredTokenError):
        service.verify_token(expired)


def test_invalid_token_raises(jwt_service: JWTService) -> None:
    with pytest.raises(InvalidTokenError):
        jwt_service.verify_token("not-a-valid-token")


def test_generate_refresh_token_is_unique(jwt_service: JWTService) -> None:
    first = jwt_service.generate_refresh_token()
    second = jwt_service.generate_refresh_token()

    assert first != second
    assert len(first) >= 32


def test_refresh_token_expiry_is_in_future(jwt_service: JWTService) -> None:
    expiry = jwt_service.get_refresh_token_expiry()
    assert expiry > datetime.now(tz=UTC)


def test_decode_token_returns_payload(jwt_service: JWTService) -> None:
    token = jwt_service.create_access_token(
        user_id=uuid4(), email="user@example.com", role=Role.USER
    )
    payload = jwt_service.decode_token(token)
    assert payload["token_type"] == "access"


def _encode(jwt_settings: Settings, **claims: object) -> str:
    now = datetime.now(tz=UTC)
    base = {
        "iss": jwt_settings.jwt_issuer,
        "aud": jwt_settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    base.update(claims)
    return jwt.encode(base, jwt_settings.secret_key, algorithm=jwt_settings.jwt_algorithm)


def test_extract_user_id_rejects_non_access_token(
    jwt_service: JWTService,
    jwt_settings: Settings,
) -> None:
    token = _encode(jwt_settings, token_type="refresh", user_id=str(uuid4()))
    with pytest.raises(InvalidTokenError):
        jwt_service.extract_user_id(token)


def test_extract_user_id_rejects_missing_user_id(
    jwt_service: JWTService,
    jwt_settings: Settings,
) -> None:
    token = _encode(jwt_settings, token_type="access")
    with pytest.raises(InvalidTokenError):
        jwt_service.extract_user_id(token)
