"""Auth-owned ``users`` table stub for FK resolution.

User Service does not own identity and must not import Auth ORM models.
Registering only ``users.id`` on the shared MetaData lets
``ForeignKey("users.id")`` on ``user_profiles`` resolve at runtime.
"""

from __future__ import annotations

from sqlalchemy import Column, Table
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from shared.database import Base

if "users" not in Base.metadata.tables:
    Table(
        "users",
        Base.metadata,
        Column("id", PGUUID(as_uuid=True), primary_key=True),
    )
