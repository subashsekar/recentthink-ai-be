"""Integration tests for authentication HTTP endpoints with a live database."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.database import get_db


@pytest.fixture
def auth_api_client(db_session: object) -> Iterator[TestClient]:
    """Provide a test client backed by the rolled-back CRUD test session."""
    from app.main import app

    def override_get_db() -> Iterator[object]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.db
def test_auth_register_login_refresh_logout_me_flow(
    auth_api_client: TestClient,
) -> None:
    email = "phase3-flow@example.com"
    password = "SecurePass1"

    register_response = auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Flow",
            "last_name": "Test",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201
    assert register_response.json()["user"]["email"] == email

    login_response = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["token_type"] == "bearer"

    me_response = auth_api_client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == email

    refresh_response = auth_api_client.post(
        "/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()

    logout_response = auth_api_client.post(
        "/auth/logout",
        json={"refresh_token": refresh_data["refresh_token"]},
    )
    assert logout_response.status_code == 200

    revoked_refresh = auth_api_client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_data["refresh_token"]},
    )
    assert revoked_refresh.status_code == 401


@pytest.mark.db
def test_refresh_token_reuse_revokes_all_sessions(
    auth_api_client: TestClient,
) -> None:
    """Reusing a rotated (revoked) refresh token kills every session."""
    email = "phase3-reuse@example.com"
    password = "SecurePass1"

    auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Reuse",
            "last_name": "Test",
            "email": email,
            "password": password,
        },
    )
    login_data = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()

    # Rotate once: the original refresh token is now revoked.
    first_refresh = auth_api_client.post(
        "/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    ).json()

    # Reusing the original (now revoked) token is treated as compromise.
    reuse = auth_api_client.post(
        "/auth/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert reuse.status_code == 401

    # The whole family is revoked, so the rotated token no longer works either.
    after_reuse = auth_api_client.post(
        "/auth/refresh",
        json={"refresh_token": first_refresh["refresh_token"]},
    )
    assert after_reuse.status_code == 401


@pytest.mark.db
def test_refresh_tokens_are_not_stored_in_plaintext(
    auth_api_client: TestClient,
    db_session: object,
) -> None:
    """The database must never contain the raw refresh token value."""
    from sqlalchemy import select

    from app.models.refresh_token import RefreshToken
    from app.security.tokens import hash_token

    email = "phase3-hash@example.com"
    password = "SecurePass1"
    auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Hash",
            "last_name": "Test",
            "email": email,
            "password": password,
        },
    )
    login_data = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()
    raw_token = login_data["refresh_token"]

    stored_values = list(db_session.scalars(select(RefreshToken.token)).all())
    assert raw_token not in stored_values
    assert hash_token(raw_token) in stored_values


@pytest.mark.db
def test_duplicate_registration_returns_409(
    auth_api_client: TestClient,
) -> None:
    """Registering an existing email over HTTP returns 409 Conflict."""
    email = "phase3-dup@example.com"
    body = {
        "first_name": "Dup",
        "last_name": "Test",
        "email": email,
        "password": "SecurePass1",
    }
    first = auth_api_client.post("/auth/register", json=body)
    assert first.status_code == 201

    second = auth_api_client.post("/auth/register", json=body)
    assert second.status_code == 409
