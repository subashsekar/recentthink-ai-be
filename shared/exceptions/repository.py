"""Repository-layer exception types."""

from __future__ import annotations

from shared.exceptions.base import DatabaseException


class RepositoryError(DatabaseException):
    """Base exception for repository operations."""


class DuplicateEmailError(RepositoryError):
    """Raised when inserting or updating a record with a duplicate email."""


class DuplicateUsernameError(RepositoryError):
    """Raised when inserting or updating a profile with a duplicate username."""


class RecordNotFoundError(RepositoryError):
    """Raised when a requested record does not exist."""
