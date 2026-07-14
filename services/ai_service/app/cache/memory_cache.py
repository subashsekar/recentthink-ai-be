"""In-memory TTL cache provider (free, process-local)."""

from __future__ import annotations

import sys
import time
from typing import Any

from cachetools import TTLCache

from app.cache.cache_provider import CacheProvider
from shared.logging import get_logger

logger = get_logger(__name__)

# TTLCache applies one TTL ceiling to every entry; per-key expiry is enforced
# via ``expires_at`` on read. 30 days covers the longest feature TTL.
_TTL_CEILING_SECONDS = 2_592_000


class MemoryCacheProvider(CacheProvider):
    """Process-local cache backed by :class:`cachetools.TTLCache`."""

    def __init__(
        self,
        *,
        max_entries: int = 1000,
        default_ttl: int = 86_400,
    ) -> None:
        self._default_ttl = max(1, int(default_ttl))
        self._max_entries = max(1, int(max_entries))
        self._store: TTLCache[str, tuple[Any, float]] = TTLCache(
            maxsize=self._max_entries,
            ttl=_TTL_CEILING_SECONDS,
        )
        self._expired_count = 0
        self._eviction_count = 0

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() >= expires_at:
            self._store.pop(key, None)
            self._expired_count += 1
            logger.info("cache_expired key=%s", key)
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        resolved_ttl = self._default_ttl if ttl is None else max(1, int(ttl))
        expires_at = time.time() + resolved_ttl
        before = len(self._store)
        will_evict = before >= self._max_entries and key not in self._store
        self._store[key] = (value, expires_at)
        if will_evict and len(self._store) <= before:
            self._eviction_count += 1
            logger.info("cache_eviction max_entries=%s", self._max_entries)

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    def statistics(self) -> dict[str, Any]:
        return {
            "entries": len(self._store),
            "max_entries": self._max_entries,
            "default_ttl": self._default_ttl,
            "expired_entries": self._expired_count,
            "evictions": self._eviction_count,
            "memory_usage_bytes": self._estimate_memory_bytes(),
        }

    def _estimate_memory_bytes(self) -> int:
        """Best-effort shallow size estimate of cached payloads."""
        total = sys.getsizeof(self._store)
        for key, (value, expires_at) in list(self._store.items()):
            total += sys.getsizeof(key) + sys.getsizeof(expires_at)
            total += sys.getsizeof(value)
        return total
