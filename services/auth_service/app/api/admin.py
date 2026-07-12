"""Administrator authentication HTTP routes."""

from __future__ import annotations

from app.core.rate_limit import LOGIN_RATE_LIMIT, limiter
from app.dependencies.auth import get_admin_auth_service, require_admin, require_super_admin
from app.models.user import User
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutRequest,
    AdminLogoutResponse,
    AdminProfileResponse,
    AdminRefreshRequest,
    AdminRefreshResponse,
    ErrorResponse,
)
from app.schemas.common import MessageResponse
from app.services.admin_auth_service import AdminAuthService
from fastapi import APIRouter, Depends, Request, status

router = APIRouter(prefix="/admin", tags=["admin"])

_ERROR_RESPONSES: dict[int | str, dict[str, type[ErrorResponse]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(LOGIN_RATE_LIMIT)  # type: ignore[untyped-decorator]
def admin_login(
    request: Request,
    payload: AdminLoginRequest,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminLoginResponse:
    """Authenticate an administrator with email and password."""
    return admin_auth_service.login(payload)


@router.post(
    "/refresh",
    response_model=AdminRefreshResponse,
    responses=_ERROR_RESPONSES,
)
def admin_refresh(
    payload: AdminRefreshRequest,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminRefreshResponse:
    """Issue new admin credentials using a valid refresh token."""
    return admin_auth_service.refresh(payload)


@router.post(
    "/logout",
    response_model=AdminLogoutResponse,
    responses=_ERROR_RESPONSES,
)
def admin_logout(
    payload: AdminLogoutRequest,
    admin_auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminLogoutResponse:
    """Revoke the provided admin refresh token."""
    admin_auth_service.logout(payload)
    return AdminLogoutResponse()


@router.get(
    "/me",
    response_model=AdminProfileResponse,
    responses=_ERROR_RESPONSES,
)
def get_admin_me(
    current_admin: User = Depends(require_admin),
) -> AdminProfileResponse:
    """Return the authenticated administrator's profile."""
    return AdminProfileResponse.model_validate(current_admin)


@router.get(
    "/users",
    response_model=MessageResponse,
    responses=_ERROR_RESPONSES,
    include_in_schema=False,
    deprecated=True,
)
def admin_users_placeholder(
    _current_admin: User = Depends(require_admin),
) -> MessageResponse:
    """Deprecated: user management lives on Admin Service via the Gateway."""
    return MessageResponse(
        message="Use Admin Service endpoints via Gateway /admin/users.",
    )


@router.get(
    "/management",
    response_model=MessageResponse,
    responses=_ERROR_RESPONSES,
    include_in_schema=False,
    deprecated=True,
)
def admin_management_placeholder(
    _current_super_admin: User = Depends(require_super_admin),
) -> MessageResponse:
    """Deprecated: admin management lives on Admin Service."""
    return MessageResponse(
        message="Use Admin Service endpoints via Gateway.",
    )
