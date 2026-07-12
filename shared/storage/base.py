"""Storage backend protocol and shared errors."""

from __future__ import annotations

from typing import Protocol


class StorageError(Exception):
    """Raised when a storage operation fails."""


class StorageBackend(Protocol):
    """Minimal file-storage contract used by services.

    Implementations persist opaque bytes under a caller-chosen key and return a
    publicly reachable URL. Binary content is never stored in PostgreSQL.
    """

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Persist ``data`` under ``key`` and return its public URL."""

    def delete(self, key: str) -> None:
        """Remove the object identified by ``key`` if it exists."""

    def url_for(self, key: str) -> str:
        """Return the public URL for an existing object key."""
