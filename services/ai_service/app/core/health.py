"""Health check business logic."""

from __future__ import annotations

from app.core.config import SERVICE_NAME

from shared.schemas.health import HealthResponse, build_health_response


def get_health_status() -> HealthResponse:
    """Build the current service health payload."""
    return build_health_response(SERVICE_NAME)
