"""Add mode_id to ai_sessions for per-conversation coaching mode.

Revision ID: j1e6f7a8b9c0
Revises: i0d5e6f7a8b9
Create Date: 2026-07-09 11:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "j1e6f7a8b9c0"
down_revision: str | None = "i0d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_sessions",
        sa.Column("mode_id", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_sessions", "mode_id")
