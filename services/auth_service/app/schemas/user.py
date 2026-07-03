"""User database-layer Pydantic schemas.

These schemas model the persistence boundary (repository input/output). They are
NOT intended to be returned directly from HTTP responses — see
``app.schemas.responses`` for API-facing schemas that never expose credential
material such as ``password_hash``.
"""

from __future__ import annotations

from uuid import UUID

from app.models.enums import Role
from app.schemas.common import BaseSchema, TimestampSchema
from pydantic import EmailStr, Field


class UserBase(BaseSchema):
    """Fields shared across user schemas (never includes ``password_hash``)."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    role: Role = Role.USER
    is_verified: bool = False
    is_active: bool = True


class UserCreate(UserBase):
    """Fields required to persist a new user record (repository input)."""

    password_hash: str = Field(..., min_length=1, max_length=255)


class UserRead(UserBase, TimestampSchema):
    """User record returned from the database layer.

    Deliberately excludes ``password_hash`` so the hashed credential is never
    serialized, even at the repository boundary.
    """

    id: UUID


class UserUpdate(BaseSchema):
    """Fields for partially updating a user record (repository input)."""

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password_hash: str | None = Field(default=None, min_length=1, max_length=255)
    role: Role | None = None
    is_verified: bool | None = None
    is_active: bool | None = None
