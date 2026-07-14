"""Backward-compatible re-export of cache statistics."""

from app.cache.cache_statistics import CacheStatistics, CacheStats, now_ms

__all__ = ["CacheStatistics", "CacheStats", "now_ms"]
