"""Administrator authentication use-case service."""

from __future__ import annotations

from app.models.enums import Role
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminLogoutRequest,
    AdminProfileResponse,
    AdminRefreshRequest,
    AdminRefreshResponse,
)
from app.schemas.auth import LoginRequest, LogoutRequest
from app.schemas.token import RefreshTokenRequest
from app.services.auth_service import AuthService

from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)

_ADMIN_ROLES = frozenset({Role.ADMIN, Role.SUPER_ADMIN})


class AdminAuthService:
    """Orchestrates admin login, token refresh, and logout.

    Composes :class:`AuthService` so token issuance, hashing, rotation, and
    reuse detection are not duplicated.
    """

    def __init__(self, auth_service: AuthService) -> None:
        self._auth = auth_service

    def login(self, request: AdminLoginRequest) -> AdminLoginResponse:
        """Authenticate admin credentials and issue tokens."""
        result = self._auth.login(
            LoginRequest(email=request.email, password=request.password),
            required_roles=_ADMIN_ROLES,
        )
        logger.info("Admin login succeeded email=%s", request.email)
        log_security_event("admin_login", email=str(request.email))
        return AdminLoginResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            admin=AdminProfileResponse.model_validate(result.user),
        )

    def refresh(self, request: AdminRefreshRequest) -> AdminRefreshResponse:
        """Validate an admin refresh token, rotate it, and return new credentials."""
        result = self._auth.refresh(
            RefreshTokenRequest(refresh_token=request.refresh_token),
            required_roles=_ADMIN_ROLES,
        )
        logger.info("Admin token refreshed")
        return AdminRefreshResponse(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
        )

    def logout(self, request: AdminLogoutRequest) -> None:
        """Revoke the provided admin refresh token."""
        self._auth.logout(LogoutRequest(refresh_token=request.refresh_token))
        logger.info("Admin logout succeeded")
