"""Shared exception types and error handlers."""

from shared.exceptions.auth import (
    AuthError,
    AuthenticationException,
    AuthorizationError,
    AuthorizationException,
    EmailAlreadyVerifiedError,
    EmailNotVerifiedError,
    ExpiredTokenError,
    ForbiddenError,
    BlockedUserError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordReuseError,
    RevokedTokenError,
    UsedTokenError,
    UserNotFoundError,
)
from shared.exceptions.base import (
    BusinessException,
    DatabaseException,
    ValidationException,
)
from shared.exceptions.email import EmailDeliveryError, EmailError
from shared.exceptions.repository import (
    DuplicateEmailError,
    DuplicateUsernameError,
    RecordNotFoundError,
    RepositoryError,
)

__all__ = [
    "AuthError",
    "AuthenticationException",
    "AuthorizationError",
    "AuthorizationException",
    "BusinessException",
    "DatabaseException",
    "DuplicateEmailError",
    "DuplicateUsernameError",
    "EmailAlreadyVerifiedError",
    "EmailDeliveryError",
    "EmailError",
    "EmailNotVerifiedError",
    "ExpiredTokenError",
    "ForbiddenError",
    "BlockedUserError",
    "InactiveUserError",
    "InvalidCredentialsError",
    "InvalidTokenError",
    "PasswordReuseError",
    "RecordNotFoundError",
    "RepositoryError",
    "RevokedTokenError",
    "UsedTokenError",
    "UserNotFoundError",
    "ValidationException",
]
