"""Add reusable AI platform tables

Revision ID: f8a3b4c5d6e7
Revises: e7f2a3b4c5d6
Create Date: 2026-07-06 15:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a3b4c5d6e7"
down_revision: str | None = "e7f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "feature",
            sa.Enum(
                "leetcode",
                "hackerrank",
                "dsa",
                "interview",
                "course_generator",
                name="ai_feature",
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "IN_PROGRESS",
                "COMPLETED",
                "FAILED",
                "MANUAL_REQUIRED",
                name="ai_session_status",
                native_enum=False,
                length=50,
            ),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("context_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_sessions")),
    )
    op.create_index(op.f("ix_ai_sessions_user_id"), "ai_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_ai_sessions_feature"), "ai_sessions", ["feature"], unique=False)

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "assistant", "system", name="ai_message_role", native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column(
            "module_name",
            sa.Enum(
                "planner",
                "llm",
                "teacher",
                "coder",
                "evaluator",
                name="ai_module_name",
                native_enum=False,
                length=50,
            ),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            name=op.f("fk_ai_messages_session_id_ai_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ai_messages")),
    )
    op.create_index(op.f("ix_ai_messages_session_id"), "ai_messages", ["session_id"], unique=False)

    op.create_table(
        "agent_execution",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "module_name",
            sa.Enum(
                "planner",
                "llm",
                "teacher",
                "coder",
                "evaluator",
                name="agent_execution_module",
                native_enum=False,
                length=50,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("SUCCESS", "FAILED", "SKIPPED", name="agent_execution_status", native_enum=False, length=50),
            nullable=False,
        ),
        sa.Column("execution_time_ms", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("token_usage", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("trace_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            name=op.f("fk_agent_execution_session_id_ai_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_execution")),
    )
    op.create_index(
        op.f("ix_agent_execution_session_id"),
        "agent_execution",
        ["session_id"],
        unique=False,
    )

    op.create_table(
        "conversation_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("history_summary", sa.Text(), nullable=True),
        sa.Column("previous_responses", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("follow_up_questions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            name=op.f("fk_conversation_memory_session_id_ai_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_conversation_memory")),
        sa.UniqueConstraint("session_id", name=op.f("uq_conversation_memory_session_id")),
    )
    op.create_index(
        op.f("ix_conversation_memory_session_id"),
        "conversation_memory",
        ["session_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_conversation_memory_user_id"),
        "conversation_memory",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature", sa.String(length=100), nullable=False),
        sa.Column("module_name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("locale", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_versions")),
        sa.UniqueConstraint(
            "feature",
            "module_name",
            "version",
            "locale",
            name=op.f("uq_prompt_versions_feature_module_version_locale"),
        ),
    )
    op.create_index(op.f("ix_prompt_versions_feature"), "prompt_versions", ["feature"], unique=False)
    op.create_index(
        op.f("ix_prompt_versions_module_name"),
        "prompt_versions",
        ["module_name"],
        unique=False,
    )

    op.create_table(
        "model_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["ai_sessions.id"],
            name=op.f("fk_model_usage_session_id_ai_sessions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_usage")),
    )
    op.create_index(op.f("ix_model_usage_session_id"), "model_usage", ["session_id"], unique=False)
    op.create_index(op.f("ix_model_usage_user_id"), "model_usage", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("model_usage")
    op.drop_table("prompt_versions")
    op.drop_table("conversation_memory")
    op.drop_table("agent_execution")
    op.drop_table("ai_messages")
    op.drop_table("ai_sessions")
