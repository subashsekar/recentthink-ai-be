"""Abstract cache provider interface.

Concrete backends (in-memory today; Redis later) implement this contract so
AI Service business logic never depends on a specific cache technology.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheProvider(ABC):
    """Unified cache contract — swap Memory for Redis without call-site changes."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return the cached value or ``None`` on miss / expiry."""

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store ``value`` under ``key`` with optional TTL in seconds."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete ``key``. Return ``True`` if a value was removed."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return ``True`` when ``key`` is present and not expired."""

    @abstractmethod
    def clear(self) -> int:
        """Remove all entries. Return count removed."""

    @abstractmethod
    def statistics(self) -> dict[str, Any]:
        """Return provider-level stats (entries, memory, etc.)."""
