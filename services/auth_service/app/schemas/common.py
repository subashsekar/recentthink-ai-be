"""Shared Pydantic schema utilities."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with ORM mode enabled."""

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Common timestamp fields for response schemas."""

    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseSchema):
    """Generic message response."""

    message: str
