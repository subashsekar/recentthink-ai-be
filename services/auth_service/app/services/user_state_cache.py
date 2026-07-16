"""Process-local user-state cache for Auth Service.

Gateway session checks call Auth on every authenticated request. Caching the
lightweight snapshot in-process (and invalidating on identity mutations) keeps
that path cheap while still reflecting block / deactivate immediately.
"""

from __future__ import annotations

import threading
from uuid import UUID

from cachetools import TTLCache

from app.schemas.user_state import UserStateResponse

# Safety-net TTL; mutations always call :func:`invalidate_user_state`.
_DEFAULT_TTL_SECONDS = 60
_MAX_ENTRIES = 10_000

_lock = threading.Lock()
_cache: TTLCache[str, UserStateResponse] = TTLCache(
    maxsize=_MAX_ENTRIES,
    ttl=_DEFAULT_TTL_SECONDS,
)


def get_cached_user_state(user_id: UUID) -> UserStateResponse | None:
    """Return a cached snapshot, or ``None`` on miss / expiry."""
    with _lock:
        return _cache.get(str(user_id))


def set_cached_user_state(state: UserStateResponse) -> None:
    """Store a snapshot under ``state.user_id``."""
    with _lock:
        _cache[str(state.user_id)] = state


def invalidate_user_state(user_id: UUID) -> None:
    """Drop a cached snapshot so the next lookup hits the database."""
    with _lock:
        _cache.pop(str(user_id), None)


def clear_user_state_cache() -> None:
    """Clear the entire cache (tests only)."""
    with _lock:
        _cache.clear()
