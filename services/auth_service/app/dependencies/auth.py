"""FastAPI dependencies for authentication."""

from __future__ import annotations

from typing import Annotated

from app.dependencies.repositories import (
    get_refresh_token_repository,
    get_user_repository,
)
from app.models.enums import Role
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService
from app.services.password_service import PasswordService
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.exceptions.auth import ForbiddenError, InactiveUserError

_bearer_scheme = HTTPBearer(auto_error=True)


def get_password_service() -> PasswordService:
    """Provide a :class:`PasswordService` instance."""
    return PasswordService()


def get_jwt_service() -> JWTService:
    """Provide a :class:`JWTService` instance."""
    return JWTService()


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository,
    ),
    password_service: PasswordService = Depends(get_password_service),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> AuthService:
    """Provide an :class:`AuthService` wired to the request-scoped repositories."""
    return AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        jwt_service=jwt_service,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the authenticated user from the bearer access token."""
    return auth_service.resolve_user_from_access_token(credentials.credentials)


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user only when the account is active."""
    if not current_user.is_active:
        raise InactiveUserError("User account is inactive.")
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Placeholder admin guard for future RBAC (Phase 4+).

    Raises an authorization error (not an authentication error) when an
    authenticated user lacks the required role.
    """
    if current_user.role not in {Role.ADMIN, Role.SUPER_ADMIN}:
        raise ForbiddenError("Admin privileges required.")
    return current_user
