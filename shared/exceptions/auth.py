"""Authentication domain exceptions."""

from __future__ import annotations


class AuthError(Exception):
    """Base class for authentication-related errors."""


class InvalidCredentialsError(AuthError):
    """Raised when email/password combination is invalid."""


class UserNotFoundError(AuthError):
    """Raised when a user record cannot be found."""


class InactiveUserError(AuthError):
    """Raised when an inactive user attempts to authenticate."""


class InvalidTokenError(AuthError):
    """Raised when a token is malformed or cannot be verified."""


class ExpiredTokenError(AuthError):
    """Raised when a token has passed its expiration time."""


class RevokedTokenError(AuthError):
    """Raised when a refresh token has been revoked."""


class AuthorizationError(AuthError):
    """Base class for authorization (permission) failures.

    Distinct from authentication errors: the caller *is* authenticated but is
    not permitted to perform the requested action.
    """


class ForbiddenError(AuthorizationError):
    """Raised when an authenticated user lacks permission for a resource."""
