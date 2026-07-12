"""Course and learning-path ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base


class Course(Base):
    """Generated learning path linked to an AI session."""

    __tablename__ = "courses"

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
    skill: Mapped[str | None] = mapped_column(String(200), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    learning_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    programming_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nested course sections from the single OpenRouter JSON response.
    overview: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    roadmap: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_weeks
    lessons: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_lessons
    quizzes: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_quizzes
    assignments: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_assignments
    projects: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_projects
    assessments: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # course_assessments
    resources: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    learning_tips: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    next_recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    adaptive: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    request_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # full course JSON snapshot

    current_week: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    current_lesson: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quizzes_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    projects_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    study_hours: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
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

    bookmarks: Mapped[list[CourseBookmark]] = relationship(
        "CourseBookmark",
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseProgress(Base):
    """Aggregated learning-path statistics per user."""

    __tablename__ = "course_progress"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False, index=True)
    courses_created: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    courses_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    lessons_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    projects_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quizzes_completed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    current_week: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    current_lesson: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    learning_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    study_hours: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", nullable=False)
    favorite_skill: Mapped[str | None] = mapped_column(String(200), nullable=True)
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class CourseBookmark(Base):
    """User bookmarks for course items (lessons, projects, resources)."""

    __tablename__ = "course_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", "item_type", "item_id", name="uq_course_bookmark_item"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    course_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
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

    course: Mapped[Course] = relationship("Course", back_populates="bookmarks")
