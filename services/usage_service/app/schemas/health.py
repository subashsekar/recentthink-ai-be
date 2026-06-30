"""Health check response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health status returned by the service root endpoint."""

    service: str
    status: str
