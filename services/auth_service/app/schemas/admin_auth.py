"""API request and response schemas for admin authentication endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import Role
from app.schemas.auth import ErrorResponse, LogoutResponse
from app.schemas.common import BaseSchema
from pydantic import EmailStr, Field

__all__ = [
    "AdminLoginRequest",
    "AdminLoginResponse",
    "AdminLogoutRequest",
    "AdminLogoutResponse",
    "AdminProfileResponse",
    "AdminRefreshRequest",
    "AdminRefreshResponse",
    "ErrorResponse",
]


class AdminLoginRequest(BaseSchema):
    """Payload for administrator login."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class AdminProfileResponse(BaseSchema):
    """Public representation of an authenticated administrator."""

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: Role
    is_verified: bool
    is_active: bool
    created_at: datetime


class AdminLoginResponse(BaseSchema):
    """Successful admin login payload: issued tokens plus the admin profile."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    admin: AdminProfileResponse


class AdminRefreshRequest(BaseSchema):
    """Payload for admin token refresh."""

    refresh_token: str = Field(..., min_length=1)


class AdminRefreshResponse(BaseSchema):
    """Successful admin token refresh payload."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AdminLogoutRequest(BaseSchema):
    """Payload for admin logout."""

    refresh_token: str = Field(..., min_length=1)


class AdminLogoutResponse(LogoutResponse):
    """Successful admin logout payload."""

    message: str = "Logged out successfully."
