"""Cache statistics collector for the AI Service in-memory cache."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheStatistics:
    """Mutable hit/miss/latency counters."""

    hits: int = 0
    misses: int = 0
    total_lookup_ms: float = 0.0
    lookup_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_hit(self, *, lookup_ms: float) -> None:
        with self._lock:
            self.hits += 1
            self.total_lookup_ms += lookup_ms
            self.lookup_count += 1

    def record_miss(self, *, lookup_ms: float) -> None:
        with self._lock:
            self.misses += 1
            self.total_lookup_ms += lookup_ms
            self.lookup_count += 1

    def snapshot(self, *, provider_stats: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            total = self.hits + self.misses
            hit_ratio = (self.hits / total) if total else 0.0
            avg_lookup = (
                self.total_lookup_ms / self.lookup_count if self.lookup_count else 0.0
            )
            payload: dict[str, Any] = {
                "hits": self.hits,
                "misses": self.misses,
                "hit_ratio": round(hit_ratio, 4),
                "average_lookup_time_ms": round(avg_lookup, 3),
            }
            if provider_stats:
                payload.update(
                    {
                        "entries": provider_stats.get("entries", 0),
                        "expired_entries": provider_stats.get("expired_entries", 0),
                        "evictions": provider_stats.get("evictions", 0),
                        "memory_usage_bytes": provider_stats.get("memory_usage_bytes", 0),
                        "max_entries": provider_stats.get("max_entries"),
                        "default_ttl": provider_stats.get("default_ttl"),
                    },
                )
            return payload


# Backward-compatible alias.
CacheStats = CacheStatistics


def now_ms() -> float:
    """High-resolution timestamp in milliseconds."""
    return time.perf_counter() * 1000
