"""API request and response schemas for authentication endpoints."""

from __future__ import annotations

import re

from app.schemas.common import BaseSchema
from app.schemas.responses import CurrentUserResponse, UserResponse
from pydantic import EmailStr, Field, field_validator


_PASSWORD_MIN_LENGTH = 8
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$",
)


class ErrorResponse(BaseSchema):
    """Consistent error payload returned by the API."""

    detail: str


class RegisterRequest(BaseSchema):
    """Payload for user registration."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=_PASSWORD_MIN_LENGTH, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Enforce minimum password complexity."""
        if len(value) < _PASSWORD_MIN_LENGTH:
            msg = f"Password must be at least {_PASSWORD_MIN_LENGTH} characters."
            raise ValueError(msg)
        if not _PASSWORD_PATTERN.match(value):
            msg = (
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit."
            )
            raise ValueError(msg)
        return value


class RegisterResponse(BaseSchema):
    """Successful registration payload."""

    message: str = "Registration successful."
    user: UserResponse


class LoginRequest(BaseSchema):
    """Payload for user login."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseSchema):
    """Successful login payload: issued tokens plus the authenticated user."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutRequest(BaseSchema):
    """Payload for user logout."""

    refresh_token: str = Field(..., min_length=1)


class LogoutResponse(BaseSchema):
    """Successful logout payload."""

    message: str = "Logged out successfully."


__all__ = [
    "CurrentUserResponse",
    "ErrorResponse",
    "LoginRequest",
    "LoginResponse",
    "LogoutRequest",
    "LogoutResponse",
    "RegisterRequest",
    "RegisterResponse",
    "UserResponse",
]
