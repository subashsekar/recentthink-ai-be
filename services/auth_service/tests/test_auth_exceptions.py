"""Tests for authentication exception handlers and dependencies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Role
from app.services.jwt_service import JWTService
from shared.exceptions.auth import (
    ExpiredTokenError,
    ForbiddenError,
    InactiveUserError,
    InvalidTokenError,
    RevokedTokenError,
    UserNotFoundError,
)


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def client_with_auth_errors() -> TestClient:
    from app.dependencies.auth import get_auth_service
    from app.main import app
    from app.services.auth_service import AuthService

    mock = MagicMock(spec=AuthService)
    app.dependency_overrides[get_auth_service] = lambda: mock
    yield TestClient(app), mock
    app.dependency_overrides.clear()


def test_refresh_revoked_token_returns_401(client_with_auth_errors: tuple) -> None:
    client, mock = client_with_auth_errors
    mock.refresh.side_effect = RevokedTokenError("Refresh token has been revoked.")

    response = client.post("/auth/refresh", json={"refresh_token": "token"})
    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()


def test_refresh_expired_token_returns_401(client_with_auth_errors: tuple) -> None:
    client, mock = client_with_auth_errors
    mock.refresh.side_effect = ExpiredTokenError("Refresh token has expired.")

    response = client.post("/auth/refresh", json={"refresh_token": "token"})
    assert response.status_code == 401


def test_inactive_user_on_login_returns_403(client_with_auth_errors: tuple) -> None:
    client, mock = client_with_auth_errors
    mock.login.side_effect = InactiveUserError("User account is inactive.")

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "SecurePass1"},
    )
    assert response.status_code == 403


def test_get_current_active_user_rejects_inactive() -> None:
    from app.dependencies.auth import get_current_active_user

    user = MagicMock()
    user.is_active = False
    user.is_blocked = False

    with pytest.raises(InactiveUserError):
        get_current_active_user(user)


def test_get_current_admin_requires_admin_role() -> None:
    from app.dependencies.auth import get_current_admin

    user = MagicMock()
    user.is_active = True
    user.is_blocked = False
    user.role = Role.USER

    with pytest.raises(ForbiddenError):
        get_current_admin(user)


def test_admin_forbidden_maps_to_403(client_with_auth_errors: tuple) -> None:
    """A ForbiddenError surfaced from a route maps to HTTP 403, not 401."""
    client, mock = client_with_auth_errors
    mock.login.side_effect = ForbiddenError("Admin privileges required.")

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "SecurePass1"},
    )
    assert response.status_code == 403


def test_resolve_user_from_access_token(client: TestClient) -> None:
    from shared.config import get_settings

    settings = get_settings()
    jwt_service = JWTService(settings=settings)
    user_id = uuid4()

    user = MagicMock()
    user.id = user_id
    user.first_name = "Resolve"
    user.last_name = "User"
    user.email = "resolve@example.com"
    user.role = Role.USER
    user.is_verified = False
    user.is_active = True
    user.is_blocked = False
    user.created_at = datetime.now(tz=UTC)
    user.updated_at = datetime.now(tz=UTC)
    user.password_changed_at = datetime.now(tz=UTC)
    token = jwt_service.create_access_token(
        user_id=user_id,
        email="resolve@example.com",
        role=Role.USER,
        password_changed_at=user.password_changed_at,
    )

    from app.dependencies.auth import get_current_active_user, get_user_repository
    from app.main import app

    mock_repo = MagicMock()
    mock_repo.get_user_by_id.return_value = user

    app.dependency_overrides[get_user_repository] = lambda: mock_repo
    app.dependency_overrides.pop(get_current_active_user, None)
    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["email"] == "resolve@example.com"


def test_stale_access_token_after_password_change_returns_401(
    client: TestClient,
) -> None:
    """Access tokens minted before a password change are rejected."""
    from shared.config import get_settings

    settings = get_settings()
    jwt_service = JWTService(settings=settings)
    user_id = uuid4()
    issued_at = datetime.now(tz=UTC) - timedelta(hours=1)

    token = jwt_service.create_access_token(
        user_id=user_id,
        email="stale@example.com",
        role=Role.USER,
        password_changed_at=issued_at,
    )

    user = MagicMock()
    user.id = user_id
    user.password_changed_at = datetime.now(tz=UTC)

    from app.dependencies.auth import get_user_repository
    from app.main import app

    mock_repo = MagicMock()
    mock_repo.get_user_by_id.return_value = user
    app.dependency_overrides[get_user_repository] = lambda: mock_repo
    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert "password change" in response.json()["detail"].lower()


def test_resolve_user_not_found_returns_404(client: TestClient) -> None:
    from shared.config import get_settings

    settings = get_settings()
    jwt_service = JWTService(settings=settings)
    token = jwt_service.create_access_token(
        user_id=uuid4(),
        email="missing@example.com",
        role=Role.USER,
    )

    from app.dependencies.auth import get_user_repository
    from app.main import app

    mock_repo = MagicMock()
    mock_repo.get_user_by_id.return_value = None
    app.dependency_overrides[get_user_repository] = lambda: mock_repo
    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_invalid_access_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert response.status_code == 401


def test_logout_invalid_token_returns_401(client_with_auth_errors: tuple) -> None:
    client, mock = client_with_auth_errors
    mock.logout.side_effect = InvalidTokenError("Invalid refresh token.")

    response = client.post("/auth/logout", json={"refresh_token": "bad"})
    assert response.status_code == 401


def test_refresh_user_not_found_returns_404(client_with_auth_errors: tuple) -> None:
    client, mock = client_with_auth_errors
    mock.refresh.side_effect = UserNotFoundError("User not found.")

    response = client.post("/auth/refresh", json={"refresh_token": "token"})
    assert response.status_code == 404


def test_database_exception_maps_to_500(client: TestClient) -> None:
    from app.dependencies.auth import get_auth_service
    from app.main import app
    from app.services.auth_service import AuthService
    from shared.exceptions.repository import RepositoryError

    mock = MagicMock(spec=AuthService)
    mock.login.side_effect = RepositoryError("connection lost")
    app.dependency_overrides[get_auth_service] = lambda: mock
    try:
        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "SecurePass1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "internal error" in response.json()["detail"].lower()


def test_authentication_exception_maps_to_401(client: TestClient) -> None:
    from app.dependencies.auth import get_auth_service
    from app.main import app
    from app.services.auth_service import AuthService
    from shared.exceptions.auth import AuthenticationException

    mock = MagicMock(spec=AuthService)
    mock.refresh.side_effect = AuthenticationException("Token rejected.")
    app.dependency_overrides[get_auth_service] = lambda: mock
    try:
        response = client.post("/auth/refresh", json={"refresh_token": "token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
