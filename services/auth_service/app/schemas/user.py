"""User database-layer Pydantic schemas."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import Role
from app.schemas.common import BaseSchema, TimestampSchema
from pydantic import EmailStr, Field


class UserCreate(BaseSchema):
    """Fields required to persist a new user record."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password_hash: str = Field(..., min_length=1, max_length=255)
    role: Role = Role.USER
    is_verified: bool = False
    is_active: bool = True


class UserRead(UserCreate, TimestampSchema):
    """User record returned from the database layer."""

    id: UUID


class UserUpdate(BaseSchema):
    """Fields for partially updating a user record."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = None
    is_verified: bool | None = None
    is_active: bool | None = None
