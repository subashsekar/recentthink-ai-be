"""Authentication database layer: users schema update and token tables

Revision ID: a3b7c9d1e2f4
Revises: 85dfe514c465
Create Date: 2026-07-02 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3b7c9d1e2f4"
down_revision: str | None = "85dfe514c465"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER_ROLE_ENUM = sa.Enum(
    "SUPER_ADMIN",
    "ADMIN",
    "USER",
    name="user_role",
    native_enum=False,
    length=50,
)


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=100), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "role",
            USER_ROLE_ENUM,
            nullable=True,
        ),
    )

    op.execute(
        """
        UPDATE users
        SET first_name = COALESCE(NULLIF(full_name, ''), 'Unknown'),
            last_name = '',
            role = 'USER'
        WHERE first_name IS NULL
        """
    )

    op.alter_column("users", "first_name", nullable=False)
    op.alter_column("users", "last_name", nullable=False)
    op.alter_column(
        "users",
        "role",
        nullable=False,
        server_default="USER",
    )

    op.drop_column("users", "full_name")
    op.drop_column("users", "phone_number")
    op.drop_column("users", "profile_image")
    op.drop_column("users", "is_blocked")
    op.drop_column("users", "total_tokens_used")
    op.drop_column("users", "total_requests")
    op.drop_column("users", "last_login")

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
    )
    op.create_index(
        "ix_refresh_tokens_token",
        "refresh_tokens",
        ["token"],
        unique=False,
    )

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_email_verification_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verification_tokens")),
        sa.UniqueConstraint("token", name=op.f("uq_email_verification_tokens_token")),
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_used", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token", name=op.f("uq_password_reset_tokens_token")),
    )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_index("ix_refresh_tokens_token", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.add_column(
        "users",
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("total_requests", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column(
            "total_tokens_used", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("profile_image", sa.String(length=512), nullable=True),
    )
    op.add_column("users", sa.Column("phone_number", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))

    op.execute(
        """
        UPDATE users
        SET full_name = TRIM(BOTH ' ' FROM first_name || ' ' || last_name)
        WHERE full_name IS NULL
        """
    )

    op.alter_column("users", "full_name", nullable=False)
    op.drop_column("users", "role")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

    op.alter_column("users", "total_requests", server_default=None)
    op.alter_column("users", "total_tokens_used", server_default=None)
    op.alter_column("users", "is_blocked", server_default=None)
