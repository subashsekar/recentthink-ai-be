"""API request and response schemas for email verification endpoints."""

from __future__ import annotations

from datetime import datetime

from app.schemas.common import BaseSchema
from pydantic import EmailStr, Field


class VerifyEmailRequest(BaseSchema):
    """Payload for confirming an email address with a verification token."""

    token: str = Field(..., min_length=1, max_length=512)


class VerifyEmailResponse(BaseSchema):
    """Successful email verification payload."""

    message: str = "Email verified successfully."


class ResendVerificationRequest(BaseSchema):
    """Payload for requesting a new verification email."""

    email: EmailStr


class ResendVerificationResponse(BaseSchema):
    """Successful resend payload."""

    message: str = "Verification email sent. Please check your inbox."


class VerificationStatusResponse(BaseSchema):
    """Current email verification state for the authenticated user."""

    verified: bool
    email: EmailStr
    verified_at: datetime | None = None


__all__ = [
    "ResendVerificationRequest",
    "ResendVerificationResponse",
    "VerificationStatusResponse",
    "VerifyEmailRequest",
    "VerifyEmailResponse",
]
