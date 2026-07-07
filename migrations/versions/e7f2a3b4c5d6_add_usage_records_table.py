"""Add usage metering tables

Revision ID: e7f2a3b4c5d6
Revises: d6e1f2a3b4c5
Create Date: 2026-07-06 13:35:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7f2a3b4c5d6"
down_revision: str | None = "d6e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("feature", sa.String(length=100), nullable=False),
        sa.Column("request_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("token_usage", sa.Integer(), server_default="0", nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), server_default="0", nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_records")),
    )
    op.create_index(
        op.f("ix_usage_records_user_id"),
        "usage_records",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_records_created_at"),
        "usage_records",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("usage_records")
