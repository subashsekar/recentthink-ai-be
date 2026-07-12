"""FastAPI dependencies for authentication."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from app.database import get_db
from app.dependencies.repositories import (
    get_email_verification_repository,
    get_password_reset_repository,
    get_refresh_token_repository,
    get_user_repository,
)
from app.models.enums import Role
from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_auth_service import AdminAuthService
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.services.email.base import EmailService
from app.services.email.factory import build_email_service
from app.services.email_verification_service import EmailVerificationService
from app.services.jwt_service import JWTService
from app.services.password_management_service import PasswordManagementService
from app.services.password_reset_service import PasswordResetService
from app.services.password_service import PasswordService
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from shared.exceptions.auth import (
    BlockedUserError,
    ForbiddenError,
    InactiveUserError,
    EmailNotVerifiedError,
)
from shared.logging.security import log_security_event

_bearer_scheme = HTTPBearer(auto_error=True)


def get_password_service() -> PasswordService:
    """Provide a :class:`PasswordService` instance."""
    return PasswordService()


def get_jwt_service() -> JWTService:
    """Provide a :class:`JWTService` instance."""
    return JWTService()


def get_email_service() -> EmailService:
    """Provide the configured :class:`EmailService` transport."""
    return build_email_service()


def get_email_verification_service(
    user_repository: UserRepository = Depends(get_user_repository),
    email_verification_repository: EmailVerificationRepository = Depends(
        get_email_verification_repository,
    ),
    email_service: EmailService = Depends(get_email_service),
) -> EmailVerificationService:
    """Provide an :class:`EmailVerificationService` for the request scope."""
    return EmailVerificationService(
        user_repository=user_repository,
        email_verification_repository=email_verification_repository,
        email_service=email_service,
    )


def get_password_reset_service(
    db: Session = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    password_reset_repository: PasswordResetRepository = Depends(
        get_password_reset_repository,
    ),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository,
    ),
    password_service: PasswordService = Depends(get_password_service),
    email_service: EmailService = Depends(get_email_service),
) -> PasswordResetService:
    """Provide a :class:`PasswordResetService` for the request scope."""
    return PasswordResetService(
        db=db,
        user_repository=user_repository,
        password_reset_repository=password_reset_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        email_service=email_service,
    )


def get_password_management_service(
    db: Session = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository,
    ),
    password_service: PasswordService = Depends(get_password_service),
) -> PasswordManagementService:
    """Provide a :class:`PasswordManagementService` for the request scope."""
    return PasswordManagementService(
        db=db,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
    )


def get_account_service(
    db: Session = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository,
    ),
    email_verification_repository: EmailVerificationRepository = Depends(
        get_email_verification_repository,
    ),
    password_reset_repository: PasswordResetRepository = Depends(
        get_password_reset_repository,
    ),
    password_service: PasswordService = Depends(get_password_service),
) -> AccountService:
    """Provide an :class:`AccountService` for the request scope."""
    return AccountService(
        db=db,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        email_verification_repository=email_verification_repository,
        password_reset_repository=password_reset_repository,
        password_service=password_service,
    )


def get_auth_service(
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository,
    ),
    password_service: PasswordService = Depends(get_password_service),
    jwt_service: JWTService = Depends(get_jwt_service),
    email_verification_service: EmailVerificationService = Depends(
        get_email_verification_service,
    ),
) -> AuthService:
    """Provide an :class:`AuthService` wired to the request-scoped repositories."""
    return AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        jwt_service=jwt_service,
        email_verification_service=email_verification_service,
    )


def get_admin_auth_service(
    auth_service: AuthService = Depends(get_auth_service),
) -> AdminAuthService:
    """Provide an :class:`AdminAuthService` composed from :class:`AuthService`."""
    return AdminAuthService(auth_service=auth_service)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the authenticated user from the bearer access token."""
    return auth_service.resolve_user_from_access_token(credentials.credentials)


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Return the authenticated user only when the account is usable."""
    if current_user.is_blocked:
        log_security_event(
            "forbidden_access",
            reason="blocked_user",
            user_id=str(current_user.id),
        )
        raise BlockedUserError("Your account has been blocked.")
    if not current_user.is_active:
        log_security_event(
            "forbidden_access",
            reason="inactive_user",
            user_id=str(current_user.id),
        )
        raise InactiveUserError("Your account has been disabled.")
    return current_user


def require_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require any authenticated, active user for protected user routes."""
    return current_user


def require_verified_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require an authenticated, active user with a verified email.

    Use this to protect sensitive features (billing, API keys, public profile
    publishing, premium actions). Unverified users receive HTTP 403 with
    ``code=EMAIL_NOT_VERIFIED``.
    """
    if not current_user.is_verified:
        log_security_event(
            "forbidden_access",
            reason="email_not_verified",
            user_id=str(current_user.id),
        )
        raise EmailNotVerifiedError(
            "Please verify your email to access this feature.",
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Return the authenticated user only when they hold an admin role."""
    if current_user.role not in {Role.ADMIN, Role.SUPER_ADMIN}:
        log_security_event(
            "forbidden_access",
            reason="insufficient_role",
            user_id=str(current_user.id),
            role=current_user.role,
        )
        raise ForbiddenError("Admin privileges required.")
    return current_user


def require_admin(
    current_admin: User = Depends(get_current_admin),
) -> User:
    """Require ADMIN or SUPER_ADMIN role for protected admin routes."""
    return current_admin


def require_super_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Require SUPER_ADMIN role for protected super-admin routes."""
    if current_user.role != Role.SUPER_ADMIN:
        log_security_event(
            "forbidden_access",
            reason="super_admin_required",
            user_id=str(current_user.id),
            role=current_user.role,
        )
        raise ForbiddenError("Super admin privileges required.")
    return current_user


def require_roles(*roles: Role) -> Callable[..., User]:
    """Return a FastAPI dependency that enforces one or more roles.

    Reusable across microservices that share the same JWT and user model::

        require_moderator = require_roles(Role.ADMIN, Role.SUPER_ADMIN)
    """
    allowed = frozenset(roles)

    def _dependency(
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if current_user.role not in allowed:
            log_security_event(
                "forbidden_access",
                reason="role_required",
                user_id=str(current_user.id),
                role=current_user.role,
                required_roles=",".join(sorted(r.value for r in allowed)),
            )
            raise ForbiddenError(
                f"Required role(s): {', '.join(sorted(r.value for r in allowed))}.",
            )
        return current_user

    return _dependency
