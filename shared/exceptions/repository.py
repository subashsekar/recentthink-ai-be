"""Repository-layer exception types."""

from __future__ import annotations


class RepositoryError(Exception):
    """Base exception for repository operations."""


class DuplicateEmailError(RepositoryError):
    """Raised when inserting or updating a record with a duplicate email."""


class RecordNotFoundError(RepositoryError):
    """Raised when a requested record does not exist."""
