"""Ensure Auth users table stub registers for FK resolution."""

from __future__ import annotations


def test_users_stub_registers_users_table() -> None:
    from shared.database import Base

    # Fresh import path after service isolation.
    import app.models.users_stub  # noqa: F401
    from app.models.profile import UserProfile

    assert "users" in Base.metadata.tables
    assert "user_profiles" in Base.metadata.tables
    fk_targets = {
        fk.column.table.name for fk in UserProfile.__table__.foreign_keys
    }
    assert "users" in fk_targets
