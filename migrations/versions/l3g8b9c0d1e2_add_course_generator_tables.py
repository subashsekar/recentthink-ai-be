"""Add courses, course_progress, and course_bookmarks tables

Revision ID: l3g8b9c0d1e2
Revises: k2f7a8b9c0d1
Create Date: 2026-07-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l3g8b9c0d1e2"
down_revision: str | None = "k2f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("skill", sa.String(length=200), nullable=True),
        sa.Column("goal", sa.String(length=500), nullable=True),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("target_level", sa.String(length=50), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("daily_hours", sa.Float(), nullable=True),
        sa.Column("learning_style", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("programming_language", sa.String(length=50), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("overview", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("roadmap", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("lessons", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quizzes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assignments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("projects", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("assessments", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resources", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("learning_tips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("next_recommendations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("adaptive", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("current_week", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_lesson", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("lessons_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quizzes_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("projects_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("study_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["ai_sessions.id"], name=op.f("fk_courses_session_id_ai_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("session_id", name=op.f("uq_courses_session_id")),
    )
    op.create_index(op.f("ix_courses_user_id"), "courses", ["user_id"], unique=False)
    op.create_index(op.f("ix_courses_session_id"), "courses", ["session_id"], unique=True)

    op.create_table(
        "course_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("courses_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("courses_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lessons_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("projects_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quizzes_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_week", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_lesson", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("learning_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("study_hours", sa.Float(), server_default="0", nullable=False),
        sa.Column("favorite_skill", sa.String(length=200), nullable=True),
        sa.Column("skills", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_progress")),
        sa.UniqueConstraint("user_id", name=op.f("uq_course_progress_user_id")),
    )
    op.create_index(op.f("ix_course_progress_user_id"), "course_progress", ["user_id"], unique=True)

    op.create_table(
        "course_bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("course_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name=op.f("fk_course_bookmarks_course_id_courses"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_bookmarks")),
        sa.UniqueConstraint("user_id", "course_id", "item_type", "item_id", name="uq_course_bookmark_item"),
    )
    op.create_index(op.f("ix_course_bookmarks_user_id"), "course_bookmarks", ["user_id"], unique=False)
    op.create_index(op.f("ix_course_bookmarks_course_id"), "course_bookmarks", ["course_id"], unique=False)


def downgrade() -> None:
    op.drop_table("course_bookmarks")
    op.drop_table("course_progress")
    op.drop_table("courses")
