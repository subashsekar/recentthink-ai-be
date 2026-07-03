"""Base exception types for domain and infrastructure errors."""

from __future__ import annotations


class BusinessException(Exception):
    """Base class for expected business-logic failures.

    Subclasses represent recoverable, user-facing errors with a stable
    ``code`` identifier suitable for structured API responses and logging.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.code = code
        super().__init__(message)


class ValidationException(BusinessException):
    """Raised when input fails domain validation outside Pydantic schemas."""


class DatabaseException(BusinessException):
    """Raised when a database or repository operation fails unexpectedly."""
