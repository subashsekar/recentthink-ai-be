"""Extend conversation_memory for Sprint 3 memory strategy.

Revision ID: g9b4c5d6e7f8
Revises: f8a3b4c5d6e7
Create Date: 2026-07-06 16:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "g9b4c5d6e7f8"
down_revision: str | None = "f8a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("conversation_memory", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column(
        "conversation_memory",
        sa.Column("recent_messages", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "conversation_memory",
        sa.Column("memory_version", sa.Integer(), server_default="1", nullable=False),
    )
    op.execute(
        "UPDATE conversation_memory SET summary = history_summary WHERE summary IS NULL AND history_summary IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_column("conversation_memory", "memory_version")
    op.drop_column("conversation_memory", "recent_messages")
    op.drop_column("conversation_memory", "summary")
