"""HTTP integration tests for authentication endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Role
from app.schemas.auth import LoginResponse, RegisterResponse, UserResponse
from app.schemas.token import RefreshTokenResponse
from app.services.auth_service import AuthService


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def auth_service_mock() -> MagicMock:
    return MagicMock(spec=AuthService)


@pytest.fixture
def client_with_auth_mock(
    auth_service_mock: MagicMock,
) -> Iterator[TestClient]:
    from app.dependencies.auth import get_auth_service
    from app.main import app

    app.dependency_overrides[get_auth_service] = lambda: auth_service_mock
    yield TestClient(app)
    app.dependency_overrides.clear()


def _sample_user_response() -> UserResponse:
    now = datetime.now(tz=UTC)
    return UserResponse(
        id=uuid4(),
        first_name="Jane",
        last_name="Doe",
        email="user@example.com",
        role=Role.USER,
        is_verified=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_register_endpoint_returns_201(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    auth_service_mock.register.return_value = RegisterResponse(
        user=_sample_user_response(),
    )

    response = client_with_auth_mock.post(
        "/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "user@example.com",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "user@example.com"
    assert "password_hash" not in data["user"]


def test_login_endpoint_returns_tokens(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    auth_service_mock.login.return_value = LoginResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        user=_sample_user_response(),
    )

    response = client_with_auth_mock.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "SecurePass1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-token"
    assert data["refresh_token"] == "refresh-token"


def test_refresh_endpoint_returns_new_tokens(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    auth_service_mock.refresh.return_value = RefreshTokenResponse(
        access_token="new-access",
        refresh_token="new-refresh",
    )

    response = client_with_auth_mock.post(
        "/auth/refresh",
        json={"refresh_token": "old-refresh"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"


def test_logout_endpoint_returns_success(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    response = client_with_auth_mock.post(
        "/auth/logout",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully."
    auth_service_mock.logout.assert_called_once()


def test_me_endpoint_returns_current_user(
    client: TestClient,
) -> None:
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Jane"
    user.last_name = "Doe"
    user.email = "user@example.com"
    user.role = Role.USER
    user.is_verified = False
    user.is_active = True
    user.created_at = datetime.now(tz=UTC)
    user.updated_at = datetime.now(tz=UTC)

    from app.dependencies.auth import get_current_active_user
    from app.main import app

    app.dependency_overrides[get_current_active_user] = lambda: user
    try:
        response = client.get("/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert "password_hash" not in data


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_register_weak_password_returns_422(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


def test_login_invalid_credentials_returns_401(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    from shared.exceptions.auth import InvalidCredentialsError

    auth_service_mock.login.side_effect = InvalidCredentialsError(
        "Invalid email or password.",
    )

    response = client_with_auth_mock.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


def test_register_duplicate_email_returns_409(
    client_with_auth_mock: TestClient,
    auth_service_mock: MagicMock,
) -> None:
    from shared.exceptions import DuplicateEmailError

    auth_service_mock.register.side_effect = DuplicateEmailError(
        "User with email 'user@example.com' already exists.",
    )

    response = client_with_auth_mock.post(
        "/auth/register",
        json={
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "user@example.com",
            "password": "SecurePass1",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_error_responses_documented_in_openapi(client: TestClient) -> None:
    """Every auth endpoint advertises the ErrorResponse schema for errors."""
    schema = client.get("/openapi.json").json()
    documented = schema["paths"]["/auth/login"]["post"]["responses"]
    for code in ("400", "401", "403", "404", "409", "422", "429", "500"):
        assert code in documented


def test_rate_limit_returns_429(auth_service_mock: MagicMock) -> None:
    """Exceeding the per-IP limit on /auth/login returns HTTP 429."""
    from app.core.rate_limit import limiter
    from app.dependencies.auth import get_auth_service
    from app.main import app

    auth_service_mock.login.return_value = LoginResponse(
        access_token="a",
        refresh_token="r",
        user=_sample_user_response(),
    )
    app.dependency_overrides[get_auth_service] = lambda: auth_service_mock

    original = limiter.enabled
    limiter.reset()
    limiter.enabled = True
    client = TestClient(app)
    try:
        statuses = [
            client.post(
                "/auth/login",
                json={"email": "user@example.com", "password": "SecurePass1"},
            ).status_code
            for _ in range(7)
        ]
    finally:
        limiter.enabled = original
        limiter.reset()
        app.dependency_overrides.clear()

    assert 429 in statuses
    assert statuses.count(200) <= 5
