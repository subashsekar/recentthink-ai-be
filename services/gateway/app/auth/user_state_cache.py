"""Optional process-local cache for Auth user-state responses.

Default TTL is ``0`` (disabled) so block / deactivate take effect on the next
request. Raise ``GATEWAY_USER_STATE_CACHE_TTL_SECONDS`` under high traffic when
a short delay is acceptable.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CachedUserState:
    user_id: UUID
    is_active: bool
    is_blocked: bool
    role: str
    pwd_ts: float


_lock = threading.Lock()
_store: dict[str, tuple[CachedUserState, float]] = {}


def get_cached(user_id: UUID) -> CachedUserState | None:
    key = str(user_id)
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() >= expires_at:
            _store.pop(key, None)
            return None
        return value


def set_cached(state: CachedUserState, *, ttl_seconds: float) -> None:
    if ttl_seconds <= 0:
        return
    with _lock:
        _store[str(state.user_id)] = (state, time.monotonic() + ttl_seconds)


def invalidate(user_id: UUID) -> None:
    with _lock:
        _store.pop(str(user_id), None)


def clear() -> None:
    with _lock:
        _store.clear()
