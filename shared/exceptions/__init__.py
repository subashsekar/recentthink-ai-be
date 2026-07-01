"""Shared exception types and error handlers."""

from shared.exceptions.repository import (
    DuplicateEmailError,
    RecordNotFoundError,
    RepositoryError,
)

__all__ = [
    "DuplicateEmailError",
    "RecordNotFoundError",
    "RepositoryError",
]
