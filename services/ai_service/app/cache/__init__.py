"""AI Service free in-memory response cache."""

from app.cache.cache_keys import (
    CACHEABLE_FEATURES,
    build_course_key,
    build_dsa_key,
    build_feature_key,
    build_hackerrank_key,
    build_leetcode_key,
    is_cacheable_feature,
)
from app.cache.cache_manager import CacheManager, get_cache_manager
from app.cache.cache_provider import CacheProvider
from app.cache.cache_statistics import CacheStatistics, CacheStats
from app.cache.memory_cache import MemoryCacheProvider

__all__ = [
    "CACHEABLE_FEATURES",
    "CacheManager",
    "CacheProvider",
    "CacheStatistics",
    "CacheStats",
    "MemoryCacheProvider",
    "build_course_key",
    "build_dsa_key",
    "build_feature_key",
    "build_hackerrank_key",
    "build_leetcode_key",
    "get_cache_manager",
    "is_cacheable_feature",
]
