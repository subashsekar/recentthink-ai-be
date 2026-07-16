"""Add chat session management fields to ai_sessions.

Revision ID: t1a2b3c4d5e6
Revises: s0n5i6j7k8l9
Create Date: 2026-07-14 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "t1a2b3c4d5e6"
down_revision: str | None = "s0n5i6j7k8l9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_sessions",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_sessions",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_sessions",
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ai_sessions_is_archived", "ai_sessions", ["is_archived"])
    op.create_index("ix_ai_sessions_is_pinned", "ai_sessions", ["is_pinned"])
    op.create_index("ix_ai_sessions_last_active_at", "ai_sessions", ["last_active_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_sessions_last_active_at", table_name="ai_sessions")
    op.drop_index("ix_ai_sessions_is_pinned", table_name="ai_sessions")
    op.drop_index("ix_ai_sessions_is_archived", table_name="ai_sessions")
    op.drop_column("ai_sessions", "last_active_at")
    op.drop_column("ai_sessions", "is_pinned")
    op.drop_column("ai_sessions", "is_archived")
