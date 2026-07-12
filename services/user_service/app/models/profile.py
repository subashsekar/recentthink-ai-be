"""User profile ORM model."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

import app.models.users_stub  # noqa: F401  — register users.id for FK resolution
from app.models.enums import CurrentStatus, PrimarySkill
from shared.database import Base
from shared.models import TimestampedModel


class UserProfile(TimestampedModel, Base):
    """Extended profile for an authenticated user.

    Identity credentials live in Auth Service ``users``. This table owns
    profile presentation, professional details, platform handles, and avatar URL.
    """

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Public profile handle used by ``GET /profile/public/{username}``.
    username: Mapped[str | None] = mapped_column(
        String(30),
        unique=True,
        nullable=True,
        index=True,
    )
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mobile_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_status: Mapped[CurrentStatus | None] = mapped_column(
        Enum(
            CurrentStatus,
            name="current_status",
            native_enum=False,
            length=50,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    college: Mapped[str | None] = mapped_column(String(200), nullable=True)
    company: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_skill: Mapped[PrimarySkill | None] = mapped_column(
        Enum(
            PrimarySkill,
            name="primary_skill",
            native_enum=False,
            length=50,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    leetcode_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hackerrank_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    github_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
