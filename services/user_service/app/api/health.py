"""Health check HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from shared.schemas.health import HealthResponse
from app.services.health_service import get_health_status

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service health status."""
    return get_health_status()
