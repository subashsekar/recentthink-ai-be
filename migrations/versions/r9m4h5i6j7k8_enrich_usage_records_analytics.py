"""Enrich usage_records for admin AI usage analytics.

Revision ID: r9m4h5i6j7k8
Revises: q8l3g4h5i6j7
Create Date: 2026-07-13 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "r9m4h5i6j7k8"
down_revision: str | None = "q8l3g4h5i6j7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "usage_records",
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "usage_records",
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "usage_records",
        sa.Column("model", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "usage_records",
        sa.Column("provider", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "usage_records",
        sa.Column(
            "estimated_cost",
            sa.Float(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "usage_records",
        sa.Column(
            "success",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_usage_records_feature"),
        "usage_records",
        ["feature"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_records_model"),
        "usage_records",
        ["model"],
        unique=False,
    )
    op.create_index(
        op.f("ix_usage_records_provider"),
        "usage_records",
        ["provider"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_records_provider"), table_name="usage_records")
    op.drop_index(op.f("ix_usage_records_model"), table_name="usage_records")
    op.drop_index(op.f("ix_usage_records_feature"), table_name="usage_records")
    op.drop_column("usage_records", "success")
    op.drop_column("usage_records", "estimated_cost")
    op.drop_column("usage_records", "provider")
    op.drop_column("usage_records", "model")
    op.drop_column("usage_records", "completion_tokens")
    op.drop_column("usage_records", "prompt_tokens")
