"""Cache health HTTP routes for the AI Service in-memory cache."""

from __future__ import annotations

from typing import Any

from app.cache import get_cache_manager
from fastapi import APIRouter

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/health")
def cache_health() -> dict[str, Any]:
    """Return cache status, entry count, memory usage, and TTL configuration."""
    return get_cache_manager().health()
