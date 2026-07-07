"""User LeetCode progress tracking ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class LeetCodeProgress(Base):
    """Aggregated LeetCode practice statistics per user."""

    __tablename__ = "leetcode_progress"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        unique=True,
        nullable=False,
        index=True,
    )
    problems_attempted: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    problems_completed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    easy_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    medium_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    hard_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    current_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    longest_streak: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )
    favorite_pattern: Mapped[str | None] = mapped_column(String(255), nullable=True)
    weak_topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    strong_topics: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
