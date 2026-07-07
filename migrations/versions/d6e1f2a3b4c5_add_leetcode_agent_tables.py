"""Add LeetCode agent tables

Revision ID: d6e1f2a3b4c5
Revises: c5d9e3f4a6b7
Create Date: 2026-07-06 13:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d6e1f2a3b4c5"
down_revision: str | None = "c5d9e3f4a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leetcode_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problem_title", sa.String(length=500), nullable=True),
        sa.Column("problem_slug", sa.String(length=255), nullable=True),
        sa.Column("problem_url", sa.String(length=2048), nullable=True),
        sa.Column("difficulty", sa.String(length=50), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("problem_description", sa.Text(), nullable=True),
        sa.Column("problem_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                "FAILED",
                "MANUAL_REQUIRED",
                name="leetcode_session_status",
                native_enum=False,
                length=50,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leetcode_sessions")),
    )
    op.create_index(
        op.f("ix_leetcode_sessions_user_id"),
        "leetcode_sessions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_leetcode_sessions_problem_slug"),
        "leetcode_sessions",
        ["problem_slug"],
        unique=False,
    )

    op.create_table(
        "leetcode_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("problems_attempted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("problems_completed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("easy_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("medium_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("hard_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("current_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("longest_streak", sa.Integer(), server_default="0", nullable=False),
        sa.Column("favorite_pattern", sa.String(length=255), nullable=True),
        sa.Column("weak_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("strong_topics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leetcode_progress")),
        sa.UniqueConstraint("user_id", name=op.f("uq_leetcode_progress_user_id")),
    )
    op.create_index(
        op.f("ix_leetcode_progress_user_id"),
        "leetcode_progress",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="chat_message_role", native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column(
            "agent_name",
            sa.Enum("planner", "teacher", "coder", "evaluator", name="agent_name", native_enum=False, length=50),
            nullable=True,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["leetcode_sessions.id"],
            name=op.f("fk_chat_messages_session_id_leetcode_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chat_messages")),
    )
    op.create_index(
        op.f("ix_chat_messages_session_id"),
        "chat_messages",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "agent_name",
            sa.Enum("planner", "teacher", "coder", "evaluator", name="agent_run_name", native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("token_usage", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("SUCCESS", "FAILED", "SKIPPED", name="agent_run_status", native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["leetcode_sessions.id"],
            name=op.f("fk_agent_runs_session_id_leetcode_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_runs")),
    )
    op.create_index(
        op.f("ix_agent_runs_session_id"),
        "agent_runs",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("chat_messages")
    op.drop_table("leetcode_progress")
    op.drop_table("leetcode_sessions")
