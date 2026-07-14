"""Unit tests for MemoryCacheProvider."""

from __future__ import annotations

import time

from app.cache.memory_cache import MemoryCacheProvider


def test_set_get_delete_exists() -> None:
    cache = MemoryCacheProvider(max_entries=10, default_ttl=60)
    cache.set("a", {"v": 1}, ttl=60)
    assert cache.get("a") == {"v": 1}
    assert cache.exists("a") is True
    assert cache.delete("a") is True
    assert cache.get("a") is None
    assert cache.exists("a") is False


def test_ttl_expiration() -> None:
    cache = MemoryCacheProvider(max_entries=10, default_ttl=60)
    cache.set("expire", "x", ttl=1)
    assert cache.get("expire") == "x"
    time.sleep(1.1)
    assert cache.get("expire") is None
    assert cache.statistics()["expired_entries"] >= 1


def test_eviction_at_max_entries() -> None:
    cache = MemoryCacheProvider(max_entries=2, default_ttl=60)
    cache.set("k1", 1)
    cache.set("k2", 2)
    cache.set("k3", 3)
    assert cache.statistics()["entries"] <= 2
    assert cache.statistics()["evictions"] >= 1


def test_clear_and_memory_stats() -> None:
    cache = MemoryCacheProvider(max_entries=10, default_ttl=30)
    cache.set("a", "hello")
    cache.set("b", "world")
    stats = cache.statistics()
    assert stats["entries"] == 2
    assert stats["memory_usage_bytes"] > 0
    assert cache.clear() == 2
    assert cache.statistics()["entries"] == 0
