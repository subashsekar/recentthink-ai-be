"""Refresh token database-layer Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.schemas.common import BaseSchema


class RefreshTokenRead(BaseSchema):
    """Refresh token record returned from the database layer."""

    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
