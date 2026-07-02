"""Admin request and response schemas."""

from __future__ import annotations

from uuid import UUID

from app.schemas.common import BaseSchema, TimestampSchema
from pydantic import EmailStr, Field


class AdminBase(BaseSchema):
    """Fields shared across admin schemas."""

    email: EmailStr
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)
    is_active: bool = True


class AdminCreate(AdminBase):
    """Payload for creating an administrator."""

    password: str = Field(..., min_length=8, max_length=128)


class AdminUpdate(BaseSchema):
    """Payload for partially updating an administrator."""

    email: EmailStr | None = None
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AdminResponse(AdminBase, TimestampSchema):
    """Administrator returned by the API."""

    id: UUID
