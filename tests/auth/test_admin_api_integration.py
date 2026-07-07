"""Integration tests for admin authentication HTTP endpoints with a live database."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from shared.config import Settings


@pytest.fixture
def admin_seed_settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        super_admin_email="super-admin@example.com",
        super_admin_password="SuperAdmin1",
        super_admin_first_name="Super",
        super_admin_last_name="Admin",
    )


@pytest.fixture
def admin_api_client(
    db_session: object,
    admin_seed_settings: Settings,
) -> Iterator[TestClient]:
    """Test client with DB session and a seeded super-admin account."""
    from app.database import get_db
    from app.main import app
    from app.services.super_admin_seed_service import seed_super_admin

    seed_super_admin(db_session, settings=admin_seed_settings)  # type: ignore[arg-type]

    def override_get_db() -> Iterator[object]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.db
def test_super_admin_seed_is_idempotent(
    db_session: object,
    admin_seed_settings: Settings,
) -> None:
    from app.models.enums import Role
    from app.repositories.user_repository import UserRepository
    from app.services.super_admin_seed_service import seed_super_admin

    first = seed_super_admin(db_session, settings=admin_seed_settings)  # type: ignore[arg-type]
    second = seed_super_admin(db_session, settings=admin_seed_settings)  # type: ignore[arg-type]

    assert first is True
    assert second is False

    users = UserRepository(db_session)  # type: ignore[arg-type]
    assert users.exists_user_with_role(Role.SUPER_ADMIN) is True


@pytest.mark.db
def test_admin_login_refresh_logout_me_flow(admin_api_client: TestClient) -> None:
    password = "SuperAdmin1"

    login_response = admin_api_client.post(
        "/admin/login",
        json={"email": "super-admin@example.com", "password": password},
    )
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["admin"]["role"] == "SUPER_ADMIN"
    assert login_data["token_type"] == "bearer"

    me_response = admin_api_client.get(
        "/admin/me",
        headers={"Authorization": f"Bearer {login_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "super-admin@example.com"

    refresh_response = admin_api_client.post(
        "/admin/refresh",
        json={"refresh_token": login_data["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()

    logout_response = admin_api_client.post(
        "/admin/logout",
        json={"refresh_token": refresh_data["refresh_token"]},
    )
    assert logout_response.status_code == 200

    revoked_refresh = admin_api_client.post(
        "/admin/refresh",
        json={"refresh_token": refresh_data["refresh_token"]},
    )
    assert revoked_refresh.status_code == 401


@pytest.mark.db
def test_regular_user_cannot_admin_login(
    db_session: object,
    admin_api_client: TestClient,
) -> None:
    from app.models.enums import Role
    from app.repositories.user_repository import UserRepository
    from app.services.password_service import PasswordService

    email = "regular-user@example.com"
    password = "SecurePass1"
    passwords = PasswordService()
    UserRepository(db_session).create_user(  # type: ignore[arg-type]
        first_name="Regular",
        last_name="User",
        email=email,
        password_hash=passwords.hash(password),
        role=Role.USER,
        is_verified=True,
        is_active=True,
    )

    response = admin_api_client.post(
        "/admin/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 403


@pytest.mark.db
def test_regular_user_cannot_access_admin_me(
    db_session: object,
    admin_api_client: TestClient,
) -> None:
    from app.models.enums import Role
    from app.repositories.user_repository import UserRepository
    from app.services.password_service import PasswordService

    email = "me-user@example.com"
    password = "SecurePass1"
    passwords = PasswordService()
    UserRepository(db_session).create_user(  # type: ignore[arg-type]
        first_name="Me",
        last_name="User",
        email=email,
        password_hash=passwords.hash(password),
        role=Role.USER,
        is_verified=True,
        is_active=True,
    )

    login_response = admin_api_client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    me_response = admin_api_client.get(
        "/admin/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 403
