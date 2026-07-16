"""Comprehensive RBAC dependency and endpoint tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Role


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _make_user(*, role: Role = Role.USER, is_active: bool = True) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Test"
    user.last_name = "User"
    user.email = "test@example.com"
    user.role = role
    user.is_verified = True
    user.is_active = is_active
    user.is_blocked = False
    user.created_at = datetime.now(tz=UTC)
    return user


# ---------------------------------------------------------------------------
# require_user
# ---------------------------------------------------------------------------


def test_require_user_accepts_active_user() -> None:
    from app.dependencies.auth import require_user

    user = _make_user()
    assert require_user(current_user=user) is user


def test_require_user_rejects_inactive_user() -> None:
    from app.dependencies.auth import get_current_active_user

    from shared.exceptions.auth import InactiveUserError

    user = _make_user(is_active=False)
    with pytest.raises(InactiveUserError):
        get_current_active_user(current_user=user)


# ---------------------------------------------------------------------------
# require_roles factory
# ---------------------------------------------------------------------------


def test_require_roles_accepts_matching_role() -> None:
    from app.dependencies.auth import require_roles

    dep = require_roles(Role.ADMIN, Role.SUPER_ADMIN)
    admin = _make_user(role=Role.ADMIN)
    assert dep(current_user=admin) is admin


def test_require_roles_rejects_non_matching_role() -> None:
    from app.dependencies.auth import require_roles

    from shared.exceptions.auth import ForbiddenError

    dep = require_roles(Role.ADMIN)
    user = _make_user(role=Role.USER)
    with pytest.raises(ForbiddenError):
        dep(current_user=user)


# ---------------------------------------------------------------------------
# Endpoint access — USER
# ---------------------------------------------------------------------------


def test_auth_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_auth_me_accessible_to_user(client: TestClient) -> None:
    from app.dependencies.auth import require_user
    from app.main import app

    user = _make_user(role=Role.USER)
    app.dependency_overrides[require_user] = lambda: user
    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Endpoint access — ADMIN
# ---------------------------------------------------------------------------


def test_admin_me_rejects_user_role(client: TestClient) -> None:
    from app.dependencies.auth import get_current_active_user
    from app.main import app

    user = _make_user(role=Role.USER)
    app.dependency_overrides[get_current_active_user] = lambda: user
    try:
        response = client.get(
            "/admin/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_me_accepts_admin(client: TestClient) -> None:
    from app.dependencies.auth import require_admin
    from app.main import app

    admin = _make_user(role=Role.ADMIN)
    app.dependency_overrides[require_admin] = lambda: admin
    try:
        response = client.get(
            "/admin/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_admin_me_accepts_super_admin(client: TestClient) -> None:
    from app.dependencies.auth import require_admin
    from app.main import app

    super_admin = _make_user(role=Role.SUPER_ADMIN)
    app.dependency_overrides[require_admin] = lambda: super_admin
    try:
        response = client.get(
            "/admin/me",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["role"] == "SUPER_ADMIN"


# ---------------------------------------------------------------------------
# Endpoint access — SUPER_ADMIN placeholder
# ---------------------------------------------------------------------------


def test_admin_management_rejects_admin_role(client: TestClient) -> None:
    from app.dependencies.auth import get_current_active_user
    from app.main import app

    admin = _make_user(role=Role.ADMIN)
    app.dependency_overrides[get_current_active_user] = lambda: admin
    try:
        response = client.get(
            "/admin/management",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_management_accepts_super_admin(client: TestClient) -> None:
    from app.dependencies.auth import require_super_admin
    from app.main import app

    super_admin = _make_user(role=Role.SUPER_ADMIN)
    app.dependency_overrides[require_super_admin] = lambda: super_admin
    try:
        response = client.get(
            "/admin/management",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_admin_users_placeholder_requires_admin(client: TestClient) -> None:
    response = client.get("/admin/users")
    assert response.status_code == 401


def test_admin_users_placeholder_accepts_admin(client: TestClient) -> None:
    from app.dependencies.auth import require_admin
    from app.main import app

    admin = _make_user(role=Role.ADMIN)
    app.dependency_overrides[require_admin] = lambda: admin
    try:
        response = client.get(
            "/admin/users",
            headers={"Authorization": "Bearer fake-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Public endpoints remain accessible
# ---------------------------------------------------------------------------


def test_public_endpoints_do_not_require_bearer_token(client: TestClient) -> None:
    """Public routes must not return 403 for missing Authorization header."""
    assert client.post("/auth/login", json={}).status_code == 422
    assert client.post("/auth/refresh", json={}).status_code == 422
    assert client.post("/admin/login", json={}).status_code == 422
    assert client.post("/auth/forgot-password", json={}).status_code == 422
