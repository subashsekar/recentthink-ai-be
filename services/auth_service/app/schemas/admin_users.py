"""Admin-facing user management schemas (Auth Service owns identity)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import Role
from app.schemas.common import BaseSchema
from pydantic import EmailStr, Field


class AdminUserResponse(BaseSchema):
    """Safe admin view of a user identity record."""

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: Role
    is_verified: bool
    is_active: bool
    is_blocked: bool
    disabled_at: datetime | None = None
    blocked_at: datetime | None = None
    blocked_reason: str | None = None
    email_verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminUserListResponse(BaseSchema):
    """Paginated identity list for Admin Service aggregation."""

    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int


class AdminDashboardIdentityStats(BaseSchema):
    """Identity counters for the admin dashboard."""

    total_users: int
    active_users: int
    new_users_today: int
    verified_users: int
    blocked_users: int


class AdminBlockUserRequest(BaseSchema):
    """Optional reason when an admin blocks a user."""

    reason: str | None = Field(default=None, max_length=500)


class AdminReasonRequest(BaseSchema):
    """Optional reason for activate / deactivate / delete."""

    reason: str | None = Field(default=None, max_length=500)


class AdminUserIdsResponse(BaseSchema):
    """All user ids (broadcast fan-out)."""

    user_ids: list[UUID]


class AdminMutationResponse(BaseSchema):
    """Result of an admin identity mutation."""

    message: str
    user: AdminUserResponse
