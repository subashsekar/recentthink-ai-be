"""Shared Pydantic schemas used across microservices."""

from shared.schemas.health import HealthResponse, build_health_response

__all__ = ["HealthResponse", "build_health_response"]
