"""Unit tests for AdminAuthService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.enums import Role
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminLogoutRequest,
    AdminRefreshRequest,
)
from app.schemas.auth import LoginResponse
from app.schemas.responses import UserResponse
from app.schemas.token import RefreshTokenResponse
from app.services.admin_auth_service import AdminAuthService
from shared.exceptions.auth import (
    ForbiddenError,
    InvalidCredentialsError,
    InvalidTokenError,
)


@pytest.fixture
def auth_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def admin_auth_service(auth_service: MagicMock) -> AdminAuthService:
    return AdminAuthService(auth_service=auth_service)


def _sample_user_response(*, role: Role = Role.ADMIN) -> UserResponse:
    now = datetime.now(tz=UTC)
    return UserResponse(
        id=uuid4(),
        first_name="Ada",
        last_name="Admin",
        email="admin@example.com",
        role=role,
        is_verified=True,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_admin_login_success(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.login.return_value = LoginResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        user=_sample_user_response(role=Role.SUPER_ADMIN),
    )

    response = admin_auth_service.login(
        AdminLoginRequest(email="admin@example.com", password="AdminPass1"),
    )

    assert response.access_token == "access-token"
    assert response.refresh_token == "refresh-token"
    assert response.admin.email == "admin@example.com"
    assert response.admin.role is Role.SUPER_ADMIN
    assert "updated_at" not in response.admin.model_dump()
    auth_service.login.assert_called_once()
    assert auth_service.login.call_args.kwargs["required_roles"] is not None


def test_admin_login_invalid_credentials(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.login.side_effect = InvalidCredentialsError(
        "Invalid email or password.",
    )

    with pytest.raises(InvalidCredentialsError):
        admin_auth_service.login(
            AdminLoginRequest(email="admin@example.com", password="WrongPass1"),
        )


def test_admin_login_user_role_rejected(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.login.side_effect = ForbiddenError("Admin privileges required.")

    with pytest.raises(ForbiddenError):
        admin_auth_service.login(
            AdminLoginRequest(email="user@example.com", password="SecurePass1"),
        )


def test_admin_refresh_delegates_with_role_check(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.refresh.return_value = RefreshTokenResponse(
        access_token="new-access",
        refresh_token="new-refresh",
    )

    response = admin_auth_service.refresh(
        AdminRefreshRequest(refresh_token="old-refresh"),
    )

    assert response.access_token == "new-access"
    assert response.refresh_token == "new-refresh"
    auth_service.refresh.assert_called_once()
    assert auth_service.refresh.call_args.kwargs["required_roles"] is not None


def test_admin_refresh_user_role_rejected(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.refresh.side_effect = ForbiddenError("Admin privileges required.")

    with pytest.raises(ForbiddenError):
        admin_auth_service.refresh(
            AdminRefreshRequest(refresh_token="user-refresh"),
        )


def test_admin_logout_delegates_to_auth_service(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    admin_auth_service.logout(AdminLogoutRequest(refresh_token="refresh-token"))

    auth_service.logout.assert_called_once()


def test_admin_logout_invalid_token(
    admin_auth_service: AdminAuthService,
    auth_service: MagicMock,
) -> None:
    auth_service.logout.side_effect = InvalidTokenError("Invalid refresh token.")

    with pytest.raises(InvalidTokenError):
        admin_auth_service.logout(AdminLogoutRequest(refresh_token="missing"))
