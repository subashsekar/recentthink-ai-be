"""Cache TTL defaults and statistics behaviour."""

from __future__ import annotations

from app.cache.cache_manager import CacheManager
from app.cache.memory_cache import MemoryCacheProvider
from app.core.config import AIServiceSettings


def test_cache_hit_skip_path_stats() -> None:
    provider = MemoryCacheProvider(max_entries=10, default_ttl=60)
    mgr = CacheManager(
        settings=AIServiceSettings(cache_enabled=True),
        provider=provider,
    )
    key = "leetcode:abc"
    mgr.set(key, {"teacher": {"ok": True}}, ttl=60)
    assert mgr.get(key)["teacher"]["ok"] is True
    stats = mgr.statistics()
    assert stats["hits"] >= 1
    assert "hit_ratio" in stats
    assert "average_lookup_time_ms" in stats


def test_feature_ttls_match_sprint() -> None:
    settings = AIServiceSettings()
    mgr = CacheManager(
        settings=settings,
        provider=MemoryCacheProvider(max_entries=10, default_ttl=60),
    )
    assert mgr.ttl_for_feature("leetcode") == 86_400
    assert mgr.ttl_for_feature("hackerrank") == 86_400
    assert mgr.ttl_for_feature("dsa_pattern") == 604_800
    assert mgr.ttl_for_feature("course_generator") == 2_592_000
