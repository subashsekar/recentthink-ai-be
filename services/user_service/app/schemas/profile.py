"""Pydantic schemas for the User Service profile domain."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CurrentStatus, PrimarySkill
from app.utils.validators import (
    normalize_optional_text,
    normalize_platform_username,
    normalize_username,
    validate_bio,
    validate_http_url,
    validate_linkedin_url,
    validate_mobile_number,
)
from shared.exceptions.base import ValidationException


def _as_value_error(exc: ValidationException) -> ValueError:
    return ValueError(str(exc))


class ProfileCreate(BaseModel):
    """Payload used when creating a profile for the first time."""

    username: str | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    mobile_number: str | None = None
    bio: str | None = None
    current_status: CurrentStatus | None = None
    college: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    current_role: str | None = Field(default=None, max_length=200)
    experience_years: float | None = Field(default=None, ge=0, le=60)
    primary_skill: PrimarySkill | None = None
    leetcode_username: str | None = None
    hackerrank_username: str | None = None
    github_username: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def _username(cls, value: object) -> str | None:
        try:
            return normalize_username(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("first_name", "last_name", "college", "company", "current_role", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> str | None:
        if value is None:
            return None
        try:
            return normalize_optional_text(str(value))
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("bio", mode="before")
    @classmethod
    def _bio(cls, value: object) -> str | None:
        try:
            return validate_bio(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("mobile_number", mode="before")
    @classmethod
    def _mobile(cls, value: object) -> str | None:
        try:
            return validate_mobile_number(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("leetcode_username", "hackerrank_username", "github_username", mode="before")
    @classmethod
    def _platform_username(cls, value: object, info: object) -> str | None:
        field = getattr(info, "field_name", "username")
        try:
            return normalize_platform_username(
                str(value) if value is not None else None,
                field=str(field),
            )
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def _linkedin(cls, value: object) -> str | None:
        try:
            return validate_linkedin_url(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def _portfolio(cls, value: object) -> str | None:
        try:
            return validate_http_url(
                str(value) if value is not None else None,
                field="portfolio_url",
            )
        except ValidationException as exc:
            raise _as_value_error(exc) from exc


class ProfileUpdate(BaseModel):
    """Partial update payload for an existing profile."""

    username: str | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    mobile_number: str | None = None
    bio: str | None = None
    current_status: CurrentStatus | None = None
    college: str | None = Field(default=None, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    current_role: str | None = Field(default=None, max_length=200)
    experience_years: float | None = Field(default=None, ge=0, le=60)
    primary_skill: PrimarySkill | None = None
    leetcode_username: str | None = None
    hackerrank_username: str | None = None
    github_username: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None

    @field_validator("username", mode="before")
    @classmethod
    def _username(cls, value: object) -> str | None:
        try:
            return normalize_username(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("first_name", "last_name", "college", "company", "current_role", mode="before")
    @classmethod
    def _trim_text(cls, value: object) -> str | None:
        if value is None:
            return None
        try:
            return normalize_optional_text(str(value))
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("bio", mode="before")
    @classmethod
    def _bio(cls, value: object) -> str | None:
        try:
            return validate_bio(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("mobile_number", mode="before")
    @classmethod
    def _mobile(cls, value: object) -> str | None:
        try:
            return validate_mobile_number(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("leetcode_username", "hackerrank_username", "github_username", mode="before")
    @classmethod
    def _platform_username(cls, value: object, info: object) -> str | None:
        field = getattr(info, "field_name", "username")
        try:
            return normalize_platform_username(
                str(value) if value is not None else None,
                field=str(field),
            )
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def _linkedin(cls, value: object) -> str | None:
        try:
            return validate_linkedin_url(str(value) if value is not None else None)
        except ValidationException as exc:
            raise _as_value_error(exc) from exc

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def _portfolio(cls, value: object) -> str | None:
        try:
            return validate_http_url(
                str(value) if value is not None else None,
                field="portfolio_url",
            )
        except ValidationException as exc:
            raise _as_value_error(exc) from exc


class StatisticsResponse(BaseModel):
    """Read-only learning statistics aggregated from AI Service tables."""

    problems_solved: int = 0
    courses_completed: int = 0
    patterns_learned: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    learning_hours: float = 0.0
    last_active: datetime | None = None


class ProfileResponse(BaseModel):
    """Full profile visible to the owner or an admin."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    mobile_number: str | None = None
    profile_picture_url: str | None = None
    bio: str | None = None
    current_status: CurrentStatus | None = None
    college: str | None = None
    company: str | None = None
    current_role: str | None = None
    experience_years: float | None = None
    primary_skill: PrimarySkill | None = None
    leetcode_username: str | None = None
    hackerrank_username: str | None = None
    github_username: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    created_at: datetime
    updated_at: datetime


class PublicProfileResponse(BaseModel):
    """Publicly visible profile subset (no email, mobile, or internal IDs)."""

    username: str
    first_name: str | None = None
    last_name: str | None = None
    bio: str | None = None
    github_username: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    primary_skill: PrimarySkill | None = None
    profile_picture_url: str | None = None
    statistics: StatisticsResponse


class AvatarUploadResponse(BaseModel):
    """Result of an avatar upload."""

    profile_picture_url: str


class ProfileCompletionResponse(BaseModel):
    """Computed profile completion for onboarding nudges."""

    percent: int = Field(ge=0, le=100)
    completed_fields: list[str]
    missing_fields: list[str]
    is_complete: bool


class PublicProfileListItem(BaseModel):
    """Lightweight public profile row for search results."""

    username: str
    first_name: str | None = None
    last_name: str | None = None
    primary_skill: PrimarySkill | None = None
    profile_picture_url: str | None = None
    bio: str | None = None


class PublicProfileSearchResponse(BaseModel):
    """Paginated public profile search results."""

    items: list[PublicProfileListItem]
    page: int
    page_size: int
    total: int
