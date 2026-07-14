"""Usage API schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class RecordUsageRequest(BaseModel):
    """Payload for recording a usage event."""

    user_id: UUID
    service_name: str = Field(..., min_length=1, max_length=100)
    feature: str = Field(..., min_length=1, max_length=100)
    request_count: int = Field(default=1, ge=1)
    token_usage: int = Field(default=0, ge=0)
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    execution_time_ms: int = Field(default=0, ge=0)
    model: str | None = Field(default=None, max_length=255)
    provider: str | None = Field(default=None, max_length=100)
    estimated_cost: float = Field(default=0.0, ge=0)
    success: bool = True
    session_id: UUID | None = None
    # Structured per-section completion token attribution.
    section_tokens: dict[str, int] | None = None


class RecordUsageResponse(BaseModel):
    """Confirmation of a recorded usage event."""

    message: str = "Usage recorded successfully."
    id: UUID
