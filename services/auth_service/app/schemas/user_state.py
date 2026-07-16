"""Schemas for lightweight internal user-state checks."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserStateResponse(BaseModel):
    """Minimal identity snapshot for gateway session enforcement.

    Intentionally small so Auth can answer quickly and the gateway can reject
    blocked / deactivated accounts without waiting for access-token expiry.
    """

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    is_active: bool
    is_blocked: bool
    role: str
    pwd_ts: float = Field(
        default=0.0,
        description=(
            "Epoch seconds of the last password change. Gateway rejects access "
            "tokens whose pwd_ts claim is older than this value."
        ),
    )
