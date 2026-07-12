"""DSA Pattern Coach ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class PatternSession(Base):
    """Generated DSA pattern learning session linked to an AI session."""

    __tablename__ = "pattern_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    pattern_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    learning_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estimated_study_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    overview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mental_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    recognition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    visualization: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    templates: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    easy_example: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    medium_example: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    hard_example: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    common_mistakes: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    interview_tips: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    pattern_comparison: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    practice: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    quiz: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    next_pattern_recommendation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    completion_pct: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    practice_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quiz_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    study_minutes: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active", server_default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    bookmarks: Mapped[list[PatternBookmark]] = relationship(
        "PatternBookmark",
        back_populates="pattern_session",
        cascade="all, delete-orphan",
    )


class PatternProgress(Base):
    """Aggregated DSA Pattern Coach statistics per user."""

    __tablename__ = "pattern_progress"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False, index=True)
    patterns_learned: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    patterns_mastered: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    practice_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quizzes_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    average_quiz_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    learning_time_minutes: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    recommended_next_pattern: Mapped[str | None] = mapped_column(String(200), nullable=True)
    weak_patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    strong_patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    patterns: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PatternMastery(Base):
    """Per-pattern mastery tracking for a user."""

    __tablename__ = "pattern_mastery"
    __table_args__ = (UniqueConstraint("user_id", "pattern_name", name="uq_pattern_mastery_user_pattern"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    pattern_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        default="learning",
        server_default="learning",
        nullable=False,
    )  # learning | practiced | mastered
    sessions_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    practice_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quiz_attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    best_quiz_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    mastery_pct: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    last_studied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PatternBookmark(Base):
    """User bookmarks for DSA pattern learning items."""

    __tablename__ = "pattern_bookmarks"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "pattern_session_id",
            "item_type",
            "item_id",
            name="uq_pattern_bookmark_item",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    pattern_session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("pattern_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    item_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    pattern_session: Mapped[PatternSession] = relationship("PatternSession", back_populates="bookmarks")
