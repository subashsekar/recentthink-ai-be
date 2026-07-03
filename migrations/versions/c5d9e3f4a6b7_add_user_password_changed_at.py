"""Add password_changed_at to users

Adds a ``password_changed_at`` timestamp to ``users`` so access tokens can be
invalidated when a password is reset or changed. The value is embedded (as
epoch seconds) in the ``pwd_ts`` access-token claim; tokens minted before this
instant are rejected.

Revision ID: c5d9e3f4a6b7
Revises: b4c8d2e3f5a6
Create Date: 2026-07-03 16:30:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5d9e3f4a6b7"
down_revision: str | None = "b4c8d2e3f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "password_changed_at")
