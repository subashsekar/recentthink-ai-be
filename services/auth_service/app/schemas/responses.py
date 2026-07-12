"""API-facing response schemas for the Auth Service.

These are the ONLY schemas that should be returned from HTTP endpoints. They are
kept separate from the database-layer schemas (``app.schemas.user``) so that
credential material (``password_hash``) and other internal fields are never
serialized to clients.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import Role
from app.schemas.common import BaseSchema
from pydantic import EmailStr


class UserResponse(BaseSchema):
    """Public representation of a user returned by the API."""

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: Role
    is_verified: bool
    is_active: bool
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime


class CurrentUserResponse(BaseSchema):
    """Authenticated user's own profile (``GET /me``).

    Same safe surface as :class:`UserResponse`; kept as a distinct type so the
    "current user" contract can evolve independently of the generic user view.
    """

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: Role
    is_verified: bool
    is_active: bool
    is_blocked: bool = False
    created_at: datetime
    updated_at: datetime


# LoginResponse lives in ``app.schemas.auth`` for Phase 3 auth endpoints.
