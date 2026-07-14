"""Concurrency tests for the in-memory cache."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.cache.cache_manager import CacheManager
from app.cache.memory_cache import MemoryCacheProvider
from app.core.config import AIServiceSettings


def test_concurrent_set_get() -> None:
    manager = CacheManager(
        settings=AIServiceSettings(cache_enabled=True, cache_max_entries=500),
        provider=MemoryCacheProvider(max_entries=500, default_ttl=120),
    )

    def worker(i: int) -> bool:
        key = f"k-{i}"
        manager.set(key, {"i": i}, ttl=60)
        value = manager.get(key)
        return isinstance(value, dict) and value.get("i") == i

    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(worker, i) for i in range(100)]
        results = [f.result() for f in as_completed(futures)]

    assert all(results)
    stats = manager.statistics()
    assert stats["hits"] >= 100
    assert stats["entries"] >= 1


def test_concurrent_mixed_ops() -> None:
    provider = MemoryCacheProvider(max_entries=50, default_ttl=60)
    manager = CacheManager(
        settings=AIServiceSettings(cache_enabled=True),
        provider=provider,
    )

    def writer(i: int) -> None:
        manager.set(f"w-{i % 40}", i, ttl=30)

    def reader(i: int) -> None:
        manager.get(f"w-{i % 40}")

    with ThreadPoolExecutor(max_workers=12) as pool:
        jobs = [pool.submit(writer, i) for i in range(80)]
        jobs += [pool.submit(reader, i) for i in range(80)]
        for job in as_completed(jobs):
            job.result()

    assert provider.statistics()["entries"] <= 50
