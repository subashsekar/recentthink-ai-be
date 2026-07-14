# AI Service — Free In-Memory Cache

Process-local response cache using `cachetools.TTLCache`. No Redis, no paid
services. Lives entirely inside the AI Service behind a `CacheProvider`
abstraction so Redis can be added later without changing workflow code.

## Layout

```
app/cache/
├── cache_provider.py     # CacheProvider ABC
├── memory_cache.py       # MemoryCacheProvider (TTLCache)
├── cache_manager.py      # Facade used by openrouter_node
├── cache_keys.py         # Deterministic SHA-256 keys
├── cache_statistics.py   # Hits / misses / latency
└── cache_stats.py        # Backward-compatible alias
```

## Flow

```
Request → build SHA-256 key → CacheManager.get
  hit  → return cached JSON (skip OpenRouter)
  miss → OpenRouter → CacheManager.set → return
```

When `requested_sections` is set and a full response is already cached, the
node slices those sections from the cache and still **skips OpenRouter**.

## Cacheable

LeetCode Analyze, HackerRank Analyze, DSA Pattern Generation, Course Generation.

Not cached: interview sessions, follow-ups, conversation history, JWTs, PII.

## Keys (SHA-256, never raw prompts)

| Feature | Segments |
|---------|----------|
| LeetCode | problem_slug, model, prompt_version |
| HackerRank | challenge_slug, model, prompt_version |
| DSA Pattern | pattern, difficulty, model |
| Course Generator | topic, level, language, model |

## TTL

| Feature | TTL |
|---------|-----|
| LeetCode | 24h |
| HackerRank | 24h |
| DSA Pattern | 7d |
| Course Generator | 30d |
| Interview (unused) | 12h |

## Statistics

Hits, misses, hit ratio, expired entries, current entries, average lookup time.

## Health

`GET /cache/health` — status, entry count, memory usage, TTL map, statistics.

## Related token optimizations

See AI Service README — **Token Optimization**: `FEATURE_MAX_TOKENS`, incremental
`requested_sections`, and per-section token tracking.
