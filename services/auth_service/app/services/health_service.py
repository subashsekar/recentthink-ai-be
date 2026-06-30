"""Health check business logic."""

from __future__ import annotations

from app.core.config import SERVICE_NAME
from app.schemas.health import HealthResponse

HEALTHY_STATUS = "healthy"


def get_health_status() -> HealthResponse:
    """Build the current service health payload."""
    return HealthResponse(service=SERVICE_NAME, status=HEALTHY_STATUS)
