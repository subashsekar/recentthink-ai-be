"""API request and response schemas for password management endpoints."""

from __future__ import annotations

from app.schemas.common import BaseSchema
from app.schemas.password_policy import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    validate_password_strength,
)
from pydantic import EmailStr, Field, field_validator, model_validator


class ForgotPasswordRequest(BaseSchema):
    """Payload for requesting a password reset email."""

    email: EmailStr


class ForgotPasswordResponse(BaseSchema):
    """Generic success payload that does not reveal account existence."""

    message: str = (
        "If an account with that email exists, a password reset link has been sent."
    )


class ResetPasswordRequest(BaseSchema):
    """Payload for completing a password reset with a one-time token."""

    token: str = Field(..., min_length=1, max_length=512)
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Enforce minimum password complexity."""
        return validate_password_strength(value)


class ResetPasswordResponse(BaseSchema):
    """Successful password reset payload."""

    message: str = "Password reset successfully. Please log in with your new password."


class ChangePasswordRequest(BaseSchema):
    """Payload for changing the password of the authenticated user."""

    current_password: str = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    confirm_new_password: str = Field(
        ...,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
    )
    refresh_token: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Optional current refresh token to preserve this session when "
            "CHANGE_PASSWORD_KEEP_CURRENT_SESSION is enabled."
        ),
    )

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        """Enforce minimum password complexity."""
        return validate_password_strength(value)

    @model_validator(mode="after")
    def passwords_match(self) -> ChangePasswordRequest:
        """Ensure the confirmation matches the new password."""
        if self.new_password != self.confirm_new_password:
            msg = "New password and confirmation do not match."
            raise ValueError(msg)
        return self


class ChangePasswordResponse(BaseSchema):
    """Successful password change payload."""

    message: str = "Password changed successfully."


__all__ = [
    "ChangePasswordRequest",
    "ChangePasswordResponse",
    "ForgotPasswordRequest",
    "ForgotPasswordResponse",
    "ResetPasswordRequest",
    "ResetPasswordResponse",
]
