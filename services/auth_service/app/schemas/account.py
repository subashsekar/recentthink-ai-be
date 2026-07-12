"""Account disable / enable / delete / status API schemas."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema
from pydantic import EmailStr, Field


class DisableAccountRequest(BaseSchema):
    """Confirm identity with the current password before disabling."""

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        examples=["CurrentP@ssw0rd"],
        description="Current account password.",
    )


class EnableAccountRequest(BaseSchema):
    """Re-enable a self-disabled account with email + password (no active session)."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        examples=["CurrentP@ssw0rd"],
    )


class DeleteAccountRequest(BaseSchema):
    """Confirm identity and explicit intent before permanent deletion."""

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        examples=["CurrentP@ssw0rd"],
        description="Current account password.",
    )
    confirm: bool = Field(
        ...,
        examples=[True],
        description="Must be ``true`` to permanently delete the account.",
    )


class DisableAccountResponse(BaseSchema):
    """Successful account disable payload."""

    message: str = "Account disabled successfully."
    is_active: bool = False
    disabled_at: datetime | None = None


class EnableAccountResponse(BaseSchema):
    """Successful account re-enable payload."""

    message: str = "Account enabled successfully."
    is_active: bool = True
    disabled_at: datetime | None = None


class AccountStatusResponse(BaseSchema):
    """Current account active / disabled / blocked state."""

    is_active: bool
    is_blocked: bool = False
    disabled_at: datetime | None = None
    blocked_at: datetime | None = None
