"""Integration tests for authentication HTTP endpoints with a live database."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


def _verify_user(db_session: object, email: str) -> None:
    """Mark a registered user as verified so login is permitted in tests."""
    from sqlalchemy import select

    from app.models.user import User

    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_verified = True
    db_session.commit()


@pytest.fixture
def auth_api_client(db_session: object) -> Iterator[TestClient]:
    """Provide a test client backed by the rolled-back CRUD test session."""
    from app.database import get_db
    from app.main import app

    def override_get_db() -> Iterator[object]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.db
def test_auth_register_login_refresh_logout_me_flow(
    auth_api_client: TestClient,
    db_session: object,
) -> None:
    email = "phase3-flow@example.com"
    password = "SecurePass1!"

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
    _verify_user(db_session, email)

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
    db_session: object,
) -> None:
    """Reusing a rotated (revoked) refresh token kills every session."""
    email = "phase3-reuse@example.com"
    password = "SecurePass1!"

    auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Reuse",
            "last_name": "Test",
            "email": email,
            "password": password,
        },
    )
    _verify_user(db_session, email)
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
    password = "SecurePass1!"
    auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Hash",
            "last_name": "Test",
            "email": email,
            "password": password,
        },
    )
    _verify_user(db_session, email)
    login_data = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    ).json()
    raw_token = login_data["refresh_token"]

    stored_values = list(db_session.scalars(select(RefreshToken.token)).all())
    assert raw_token not in stored_values
    assert hash_token(raw_token) in stored_values


@pytest.mark.db
def test_password_reset_flow_invalidates_old_credentials(
    auth_api_client: TestClient,
    db_session: object,
) -> None:
    """Full forgot -> reset flow revokes old access/refresh tokens and password."""
    from app.dependencies.auth import get_email_service
    from app.main import app

    captured: list[object] = []

    class _CapturingEmail:
        def send_email(self, message: object) -> None:
            captured.append(message)

    app.dependency_overrides[get_email_service] = _CapturingEmail

    email = "phase6-reset@example.com"
    old_password = "SecurePass1!"
    new_password = "NewSecure2!"

    register = auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Reset",
            "last_name": "Flow",
            "email": email,
            "password": old_password,
        },
    )
    assert register.status_code == 201

    # Activate the account so login is permitted.
    _verify_user(db_session, email)

    login = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login.status_code == 200
    old_access = login.json()["access_token"]
    old_refresh = login.json()["refresh_token"]

    captured.clear()
    forgot = auth_api_client.post("/auth/forgot-password", json={"email": email})
    assert forgot.status_code == 200
    assert captured, "a password reset email should have been dispatched"
    reset_token = captured[-1].html_body.split("token=")[1].split('"')[0].split("&")[0]

    reset = auth_api_client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset.status_code == 200

    # Old refresh token is revoked.
    assert (
        auth_api_client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh},
        ).status_code
        == 401
    )
    # Old access token is rejected (invalidated by the password change).
    assert (
        auth_api_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        ).status_code
        == 401
    )
    # Old password no longer authenticates.
    assert (
        auth_api_client.post(
            "/auth/login",
            json={"email": email, "password": old_password},
        ).status_code
        == 401
    )
    # New password works.
    assert (
        auth_api_client.post(
            "/auth/login",
            json={"email": email, "password": new_password},
        ).status_code
        == 200
    )
    # The reset token is one-time use.
    assert auth_api_client.post(
        "/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherPass3!"},
    ).status_code in {400, 401}


@pytest.mark.db
def test_change_password_flow_invalidates_old_credentials(
    auth_api_client: TestClient,
    db_session: object,
) -> None:
    """Authenticated change-password revokes prior access and refresh tokens."""
    email = "phase6-change@example.com"
    old_password = "SecurePass1!"
    new_password = "NewSecure2!"

    auth_api_client.post(
        "/auth/register",
        json={
            "first_name": "Change",
            "last_name": "Flow",
            "email": email,
            "password": old_password,
        },
    )
    _verify_user(db_session, email)

    login = auth_api_client.post(
        "/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login.status_code == 200
    old_access = login.json()["access_token"]
    old_refresh = login.json()["refresh_token"]

    changed = auth_api_client.post(
        "/auth/change-password",
        headers={"Authorization": f"Bearer {old_access}"},
        json={
            "current_password": old_password,
            "new_password": new_password,
            "confirm_new_password": new_password,
        },
    )
    assert changed.status_code == 200

    # Old refresh token is revoked and old access token is rejected.
    assert (
        auth_api_client.post(
            "/auth/refresh",
            json={"refresh_token": old_refresh},
        ).status_code
        == 401
    )
    assert (
        auth_api_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {old_access}"},
        ).status_code
        == 401
    )
    # New password authenticates.
    assert (
        auth_api_client.post(
            "/auth/login",
            json={"email": email, "password": new_password},
        ).status_code
        == 200
    )


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
        "password": "SecurePass1!",
    }
    first = auth_api_client.post("/auth/register", json=body)
    assert first.status_code == 201

    second = auth_api_client.post("/auth/register", json=body)
    assert second.status_code == 409
