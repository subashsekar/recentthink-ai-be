"""Health check HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.schemas.health import GatewayHealthResponse
from app.services.health_service import get_aggregate_health, get_health_status
from shared.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness probe — gateway process is up."""
    return get_health_status()


@router.get("/health", response_model=GatewayHealthResponse)
async def health_detailed(request: Request) -> GatewayHealthResponse:
    """Readiness probe — gateway + every downstream service status."""
    return await get_aggregate_health(request)
