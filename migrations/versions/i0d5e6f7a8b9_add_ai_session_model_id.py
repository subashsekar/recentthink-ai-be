"""Add model_id to ai_sessions for per-conversation model preference.

Revision ID: i0d5e6f7a8b9
Revises: h9c4d5e6f7a8
Create Date: 2026-07-08 18:15:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i0d5e6f7a8b9"
down_revision: str | None = "h9c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_sessions",
        sa.Column("model_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_sessions", "model_id")
