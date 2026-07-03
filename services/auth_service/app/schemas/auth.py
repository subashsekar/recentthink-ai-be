"""API request and response schemas for authentication endpoints."""

from __future__ import annotations

from app.schemas.common import BaseSchema
from app.schemas.password_policy import (
    PASSWORD_MAX_LENGTH,
    PASSWORD_MIN_LENGTH,
    validate_password_strength,
)
from app.schemas.responses import CurrentUserResponse, UserResponse
from pydantic import EmailStr, Field, field_validator


class ErrorResponse(BaseSchema):
    """Consistent error payload returned by the API."""

    detail: str


class RegisterRequest(BaseSchema):
    """Payload for user registration."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Enforce minimum password complexity."""
        return validate_password_strength(value)


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
