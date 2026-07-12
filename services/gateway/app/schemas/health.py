"""Gateway health and dependency status schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ServiceStatus = Literal["healthy", "warning", "down"]


class DownstreamServiceHealth(BaseModel):
    """Health probe result for a single downstream service."""

    name: str
    status: ServiceStatus
    response_time_ms: int | None = None
    url: str
    detail: str | None = None


class GatewayHealthResponse(BaseModel):
    """Aggregated gateway + downstream health payload."""

    service: str = "gateway"
    status: ServiceStatus
    version: str
    environment: str
    services: list[DownstreamServiceHealth] = Field(default_factory=list)
