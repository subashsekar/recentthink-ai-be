"""Shared exception types and error handlers."""

from shared.exceptions.auth import (
    AuthError,
    AuthorizationError,
    ExpiredTokenError,
    ForbiddenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
    UserNotFoundError,
)
from shared.exceptions.repository import (
    DuplicateEmailError,
    RecordNotFoundError,
    RepositoryError,
)

__all__ = [
    "AuthError",
    "AuthorizationError",
    "DuplicateEmailError",
    "ExpiredTokenError",
    "ForbiddenError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "RecordNotFoundError",
    "RepositoryError",
    "RevokedTokenError",
    "UserNotFoundError",
]
