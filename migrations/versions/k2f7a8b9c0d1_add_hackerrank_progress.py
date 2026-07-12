"""Add HackerRank progress table

Revision ID: k2f7a8b9c0d1
Revises: j1e6f7a8b9c0
Create Date: 2026-07-09 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k2f7a8b9c0d1"
down_revision: str | None = "j1e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "hackerrank_progress",
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
        sa.Column("domains", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("languages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hackerrank_progress")),
        sa.UniqueConstraint("user_id", name=op.f("uq_hackerrank_progress_user_id")),
    )
    op.create_index(
        op.f("ix_hackerrank_progress_user_id"),
        "hackerrank_progress",
        ["user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("hackerrank_progress")

