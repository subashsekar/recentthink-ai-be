"""CacheManager and TTL / disable behaviour."""

from __future__ import annotations

import time

from app.cache.cache_manager import CacheManager
from app.cache.memory_cache import MemoryCacheProvider
from app.core.config import AIServiceSettings


def test_hit_miss_statistics() -> None:
    settings = AIServiceSettings(cache_enabled=True, cache_max_entries=100)
    manager = CacheManager(
        settings=settings,
        provider=MemoryCacheProvider(max_entries=100, default_ttl=60),
    )
    key = manager.build_key(
        feature="leetcode",
        model="m",
        prompt_version="v1",
        context={"slug": "two-sum"},
    )
    assert key is not None
    assert manager.get(key) is None
    manager.set(key, {"teacher": {"content": "x"}}, ttl=60)
    assert manager.get(key) == {"teacher": {"content": "x"}}
    stats = manager.statistics()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_ratio"] == 0.5


def test_interview_not_cached() -> None:
    manager = CacheManager(settings=AIServiceSettings(cache_enabled=True))
    assert (
        manager.build_key(
            feature="interview",
            model="m",
            prompt_version="v1",
            context={"role": "swe"},
        )
        is None
    )


def test_disabled_cache_skips_all_ops() -> None:
    manager = CacheManager(settings=AIServiceSettings(cache_enabled=False))
    assert manager.build_key(
        feature="leetcode",
        model="m",
        prompt_version="v1",
        context={"slug": "x"},
    ) is None
    manager.set("k", {"a": 1})
    assert manager.get("k") is None
    assert manager.exists("k") is False
    assert manager.delete("k") is False
    health = manager.health()
    assert health["status"] == "disabled"
    assert health["enabled"] is False


def test_feature_ttl_values() -> None:
    settings = AIServiceSettings()
    manager = CacheManager(settings=settings)
    assert manager.ttl_for_feature("leetcode") == settings.cache_ttl_leetcode
    assert manager.ttl_for_feature("hackerrank") == settings.cache_ttl_hackerrank
    assert manager.ttl_for_feature("dsa_pattern") == settings.cache_ttl_dsa_pattern
    assert manager.ttl_for_feature("course_generator") == settings.cache_ttl_course_generator


def test_manager_ttl_expiry() -> None:
    manager = CacheManager(
        settings=AIServiceSettings(cache_enabled=True),
        provider=MemoryCacheProvider(max_entries=10, default_ttl=60),
    )
    manager.set("t", "v", ttl=1)
    assert manager.get("t") == "v"
    time.sleep(1.1)
    assert manager.get("t") is None


def test_health_payload() -> None:
    manager = CacheManager(settings=AIServiceSettings(cache_enabled=True))
    manager.set("k", {"ok": True}, ttl=30)
    health = manager.health()
    assert health["status"] == "healthy"
    assert health["entry_count"] >= 1
    assert "ttl" in health
    assert "statistics" in health


def test_delete_exists_clear() -> None:
    manager = CacheManager(
        settings=AIServiceSettings(cache_enabled=True),
        provider=MemoryCacheProvider(max_entries=10, default_ttl=60),
    )
    manager.set("a", 1, ttl=30)
    assert manager.exists("a") is True
    assert manager.delete("a") is True
    assert manager.exists("a") is False
    manager.set("b", 2, ttl=30)
    assert manager.clear() >= 1
