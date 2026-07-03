"""Token-related API schemas."""

from __future__ import annotations

from app.schemas.common import BaseSchema
from pydantic import Field


class RefreshTokenRequest(BaseSchema):
    """Payload for refreshing an access token."""

    refresh_token: str = Field(..., min_length=1)


class RefreshTokenResponse(BaseSchema):
    """New credentials issued after a successful refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
