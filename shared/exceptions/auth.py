"""Authentication domain exceptions."""

from __future__ import annotations

from shared.exceptions.base import BusinessException


class AuthError(BusinessException):
    """Base class for authentication-related errors."""


class AuthenticationException(AuthError):
    """Base class for authentication failures (HTTP 401).

    Raised when the caller cannot be identified or credentials are invalid.
    """


class InvalidCredentialsError(AuthenticationException):
    """Raised when email/password combination is invalid."""


class UserNotFoundError(AuthError):
    """Raised when a user record cannot be found."""


class InactiveUserError(AuthError):
    """Raised when an inactive (self-disabled) user attempts to authenticate."""


class BlockedUserError(AuthError):
    """Raised when an admin-blocked user attempts to authenticate."""


class InvalidTokenError(AuthenticationException):
    """Raised when a token is malformed or cannot be verified."""


class ExpiredTokenError(AuthenticationException):
    """Raised when a token has passed its expiration time."""


class UsedTokenError(AuthError):
    """Raised when a one-time token has already been consumed."""


class RevokedTokenError(AuthenticationException):
    """Raised when a refresh token has been revoked."""


class EmailNotVerifiedError(AuthError):
    """Raised when an unverified user attempts a verification-gated action."""

    def __init__(
        self,
        message: str = "Please verify your email to access this feature.",
        *,
        code: str | None = "EMAIL_NOT_VERIFIED",
    ) -> None:
        super().__init__(message, code=code)


class EmailAlreadyVerifiedError(AuthError):
    """Raised when re-verifying an account whose email is already verified."""


class AuthorizationException(AuthError):
    """Base class for authorization (permission) failures (HTTP 403).

    Distinct from authentication errors: the caller *is* authenticated but is
    not permitted to perform the requested action.
    """


# Backward-compatible alias used throughout the existing codebase.
AuthorizationError = AuthorizationException


class ForbiddenError(AuthorizationException):
    """Raised when an authenticated user lacks permission for a resource."""


class PasswordReuseError(AuthError):
    """Raised when a new password matches the current password."""
