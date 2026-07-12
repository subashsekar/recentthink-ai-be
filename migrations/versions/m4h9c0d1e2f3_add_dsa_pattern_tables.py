"""Add DSA Pattern Coach tables

Revision ID: m4h9c0d1e2f3
Revises: l3g8b9c0d1e2
Create Date: 2026-07-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m4h9c0d1e2f3"
down_revision: str | None = "l3g8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pattern_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("pattern_name", sa.String(length=200), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=50), nullable=True),
        sa.Column("learning_style", sa.String(length=100), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("estimated_study_time", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("overview", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("mental_model", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("recognition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("visualization", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("templates", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("easy_example", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("medium_example", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("hard_example", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("common_mistakes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("interview_tips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("pattern_comparison", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("practice", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("quiz", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("next_pattern_recommendation", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("completion_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("practice_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quiz_score", sa.Float(), nullable=True),
        sa.Column("study_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            name=op.f("fk_pattern_sessions_session_id_ai_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_sessions")),
        sa.UniqueConstraint("session_id", name=op.f("uq_pattern_sessions_session_id")),
    )
    op.create_index(op.f("ix_pattern_sessions_user_id"), "pattern_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_pattern_sessions_session_id"), "pattern_sessions", ["session_id"], unique=True)
    op.create_index(op.f("ix_pattern_sessions_pattern_name"), "pattern_sessions", ["pattern_name"], unique=False)

    op.create_table(
        "pattern_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patterns_learned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("patterns_mastered", sa.Integer(), server_default="0", nullable=False),
        sa.Column("practice_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quizzes_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("average_quiz_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("learning_time_minutes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recommended_next_pattern", sa.String(length=200), nullable=True),
        sa.Column("weak_patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strong_patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_progress")),
        sa.UniqueConstraint("user_id", name=op.f("uq_pattern_progress_user_id")),
    )
    op.create_index(op.f("ix_pattern_progress_user_id"), "pattern_progress", ["user_id"], unique=True)

    op.create_table(
        "pattern_mastery",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="learning", nullable=False),
        sa.Column("sessions_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("practice_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quiz_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("best_quiz_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("mastery_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("last_studied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_mastery")),
        sa.UniqueConstraint("user_id", "pattern_name", name="uq_pattern_mastery_user_pattern"),
    )
    op.create_index(op.f("ix_pattern_mastery_user_id"), "pattern_mastery", ["user_id"], unique=False)
    op.create_index(op.f("ix_pattern_mastery_pattern_name"), "pattern_mastery", ["pattern_name"], unique=False)

    op.create_table(
        "pattern_bookmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=False),
        sa.Column("item_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["pattern_session_id"],
            ["pattern_sessions.id"],
            name=op.f("fk_pattern_bookmarks_pattern_session_id_pattern_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_bookmarks")),
        sa.UniqueConstraint(
            "user_id",
            "pattern_session_id",
            "item_type",
            "item_id",
            name="uq_pattern_bookmark_item",
        ),
    )
    op.create_index(op.f("ix_pattern_bookmarks_user_id"), "pattern_bookmarks", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_pattern_bookmarks_pattern_session_id"),
        "pattern_bookmarks",
        ["pattern_session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("pattern_bookmarks")
    op.drop_table("pattern_mastery")
    op.drop_table("pattern_progress")
    op.drop_table("pattern_sessions")
