"""User request and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema, TimestampSchema
from pydantic import EmailStr, Field


class UserBase(BaseSchema):
    """Fields shared across user schemas."""

    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone_number: str | None = Field(default=None, max_length=20)
    is_verified: bool = False
    is_active: bool = True
    is_blocked: bool = False


class UserCreate(UserBase):
    """Payload for creating a user."""

    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseSchema):
    """Payload for partially updating a user."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone_number: str | None = Field(default=None, max_length=20)
    is_verified: bool | None = None
    is_active: bool | None = None
    is_blocked: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserResponse(UserBase, TimestampSchema):
    """User returned by the API."""

    id: UUID
    total_tokens_used: int
    total_requests: int
    last_login: datetime | None = None
