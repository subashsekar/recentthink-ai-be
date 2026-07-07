"""Health check HTTP routes."""

from __future__ import annotations

from app.core.health import get_health_status
from fastapi import APIRouter

from shared.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service health status."""
    return get_health_status()
