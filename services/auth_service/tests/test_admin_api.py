"""HTTP tests for administrator authentication endpoints."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Role
from app.schemas.admin_auth import (
    AdminLoginResponse,
    AdminProfileResponse,
    AdminRefreshResponse,
)
from app.services.admin_auth_service import AdminAuthService


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


@pytest.fixture
def admin_auth_service_mock() -> MagicMock:
    return MagicMock(spec=AdminAuthService)


@pytest.fixture
def client_with_admin_mock(
    admin_auth_service_mock: MagicMock,
) -> Iterator[TestClient]:
    from app.dependencies.auth import get_admin_auth_service
    from app.main import app

    app.dependency_overrides[get_admin_auth_service] = (
        lambda: admin_auth_service_mock
    )
    yield TestClient(app)
    app.dependency_overrides.clear()


def _sample_admin_profile(*, role: Role = Role.ADMIN) -> AdminProfileResponse:
    return AdminProfileResponse(
        id=uuid4(),
        first_name="Ada",
        last_name="Admin",
        email="admin@example.com",
        role=role,
        is_verified=True,
        is_active=True,
        created_at=datetime.now(tz=UTC),
    )


def test_admin_login_returns_tokens_and_profile(
    client_with_admin_mock: TestClient,
    admin_auth_service_mock: MagicMock,
) -> None:
    admin_auth_service_mock.login.return_value = AdminLoginResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        admin=_sample_admin_profile(),
    )

    response = client_with_admin_mock.post(
        "/admin/login",
        json={"email": "admin@example.com", "password": "AdminPass1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-token"
    assert data["refresh_token"] == "refresh-token"
    assert data["admin"]["email"] == "admin@example.com"
    assert "password_hash" not in data["admin"]


def test_admin_login_invalid_credentials_returns_401(
    client_with_admin_mock: TestClient,
    admin_auth_service_mock: MagicMock,
) -> None:
    from shared.exceptions.auth import InvalidCredentialsError

    admin_auth_service_mock.login.side_effect = InvalidCredentialsError(
        "Invalid email or password.",
    )

    response = client_with_admin_mock.post(
        "/admin/login",
        json={"email": "admin@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


def test_admin_login_user_role_returns_403(
    client_with_admin_mock: TestClient,
    admin_auth_service_mock: MagicMock,
) -> None:
    from shared.exceptions.auth import ForbiddenError

    admin_auth_service_mock.login.side_effect = ForbiddenError(
        "Admin privileges required.",
    )

    response = client_with_admin_mock.post(
        "/admin/login",
        json={"email": "user@example.com", "password": "SecurePass1"},
    )
    assert response.status_code == 403


def test_admin_refresh_returns_new_tokens(
    client_with_admin_mock: TestClient,
    admin_auth_service_mock: MagicMock,
) -> None:
    admin_auth_service_mock.refresh.return_value = AdminRefreshResponse(
        access_token="new-access",
        refresh_token="new-refresh",
    )

    response = client_with_admin_mock.post(
        "/admin/refresh",
        json={"refresh_token": "old-refresh"},
    )

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"


def test_admin_logout_returns_success(
    client_with_admin_mock: TestClient,
    admin_auth_service_mock: MagicMock,
) -> None:
    response = client_with_admin_mock.post(
        "/admin/logout",
        json={"refresh_token": "refresh-token"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully."
    admin_auth_service_mock.logout.assert_called_once()


def test_admin_me_returns_profile_for_admin(
    client: TestClient,
) -> None:
    admin = MagicMock()
    admin.id = uuid4()
    admin.first_name = "Ada"
    admin.last_name = "Admin"
    admin.email = "admin@example.com"
    admin.role = Role.ADMIN
    admin.is_verified = True
    admin.is_active = True
    admin.created_at = datetime.now(tz=UTC)

    from app.dependencies.auth import require_admin
    from app.main import app

    app.dependency_overrides[require_admin] = lambda: admin
    try:
        response = client.get(
            "/admin/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "ADMIN"
    assert "updated_at" not in data


def test_admin_me_user_role_returns_403(client: TestClient) -> None:
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
        response = client.get(
            "/admin/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/admin/me")
    assert response.status_code == 401


def test_require_super_admin_rejects_admin_role() -> None:
    from app.dependencies.auth import require_super_admin

    admin = MagicMock()
    admin.role = Role.ADMIN

    with pytest.raises(Exception) as exc_info:
        require_super_admin(current_user=admin)

    from shared.exceptions.auth import ForbiddenError

    assert isinstance(exc_info.value, ForbiddenError)


def test_require_super_admin_accepts_super_admin() -> None:
    from app.dependencies.auth import require_super_admin

    super_admin = MagicMock()
    super_admin.role = Role.SUPER_ADMIN

    result = require_super_admin(current_user=super_admin)
    assert result is super_admin
