"""Gateway Pydantic schemas."""

from app.schemas.health import DownstreamServiceHealth, GatewayHealthResponse

__all__ = ["DownstreamServiceHealth", "GatewayHealthResponse"]
