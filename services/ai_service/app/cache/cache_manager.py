"""Cache manager — unified facade over :class:`CacheProvider`.

Default backend is in-memory ``TTLCache``. A Redis provider can be injected later
without changing OpenRouter / workflow call sites.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.cache.cache_keys import build_feature_key, is_cacheable_feature
from app.cache.cache_provider import CacheProvider
from app.cache.cache_statistics import CacheStatistics, now_ms
from app.cache.memory_cache import MemoryCacheProvider
from app.core.config import AIServiceSettings, get_ai_settings
from shared.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Single entry point for AI response caching."""

    def __init__(
        self,
        *,
        settings: AIServiceSettings | None = None,
        provider: CacheProvider | None = None,
        stats: CacheStatistics | None = None,
    ) -> None:
        self._settings = settings or get_ai_settings()
        self._provider = provider or MemoryCacheProvider(
            max_entries=self._settings.cache_max_entries,
            default_ttl=self._settings.cache_default_ttl,
        )
        self._stats = stats or CacheStatistics()

    @property
    def enabled(self) -> bool:
        return bool(self._settings.cache_enabled)

    @property
    def provider(self) -> CacheProvider:
        return self._provider

    def ttl_for_feature(self, feature: str) -> int:
        mapping = {
            "leetcode": self._settings.cache_ttl_leetcode,
            "hackerrank": self._settings.cache_ttl_hackerrank,
            "dsa": self._settings.cache_ttl_dsa_pattern,
            "dsa_pattern": self._settings.cache_ttl_dsa_pattern,
            "course_generator": self._settings.cache_ttl_course_generator,
            "course": self._settings.cache_ttl_course_generator,
            "interview": self._settings.cache_ttl_interview,
        }
        return mapping.get(feature.strip().lower(), self._settings.cache_default_ttl)

    def build_key(
        self,
        *,
        feature: str,
        model: str,
        prompt_version: str,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        message: str = "",
    ) -> str | None:
        if not self.enabled or not is_cacheable_feature(feature):
            return None
        return build_feature_key(
            feature=feature,
            model=model,
            prompt_version=prompt_version,
            context=context,
            metadata=metadata,
            message=message,
        )

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None
        start = now_ms()
        value = self._provider.get(key)
        elapsed = now_ms() - start
        if value is None:
            self._stats.record_miss(lookup_ms=elapsed)
            logger.info("cache_miss key=%s", key)
            return None
        self._stats.record_hit(lookup_ms=elapsed)
        logger.info("cache_hit key=%s", key)
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        if not self.enabled:
            return
        self._provider.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        if not self.enabled:
            return False
        return self._provider.delete(key)

    def exists(self, key: str) -> bool:
        if not self.enabled:
            return False
        return self._provider.exists(key)

    def clear(self) -> int:
        return self._provider.clear()

    def statistics(self) -> dict[str, Any]:
        return self._stats.snapshot(provider_stats=self._provider.statistics())

    def health(self) -> dict[str, Any]:
        provider_stats = self._provider.statistics()
        return {
            "status": "healthy" if self.enabled else "disabled",
            "enabled": self.enabled,
            "backend": type(self._provider).__name__,
            "entry_count": provider_stats.get("entries", 0),
            "memory_usage_bytes": provider_stats.get("memory_usage_bytes", 0),
            "max_entries": provider_stats.get("max_entries"),
            "default_ttl": provider_stats.get("default_ttl"),
            "ttl": {
                "leetcode": self._settings.cache_ttl_leetcode,
                "hackerrank": self._settings.cache_ttl_hackerrank,
                "dsa_pattern": self._settings.cache_ttl_dsa_pattern,
                "course_generator": self._settings.cache_ttl_course_generator,
                "interview": self._settings.cache_ttl_interview,
                "default": self._settings.cache_default_ttl,
            },
            "statistics": self.statistics(),
        }


@lru_cache(maxsize=1)
def get_cache_manager() -> CacheManager:
    """Return the process-wide :class:`CacheManager` singleton."""
    return CacheManager()
