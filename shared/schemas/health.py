"""Shared health-check response schema."""

from __future__ import annotations

from pydantic import BaseModel

HEALTHY_STATUS = "healthy"


class HealthResponse(BaseModel):
    """Health status returned by service health endpoints."""

    service: str
    status: str


def build_health_response(
    service_name: str,
    status: str = HEALTHY_STATUS,
) -> HealthResponse:
    """Build a standard health payload for a microservice."""
    return HealthResponse(service=service_name, status=status)
