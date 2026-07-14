"""Add section_tokens JSONB to usage_records for per-processor attribution.

Revision ID: s0n5i6j7k8l9
Revises: r9m4h5i6j7k8
Create Date: 2026-07-14 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "s0n5i6j7k8l9"
down_revision: str | None = "r9m4h5i6j7k8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usage_records",
        sa.Column(
            "section_tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("usage_records", "section_tokens")
