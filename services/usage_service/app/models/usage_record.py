"""Usage metering ORM model."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from shared.models import CreatedAtModel


class UsageRecord(CreatedAtModel, Base):
    """Per-request usage metering record."""

    __tablename__ = "usage_records"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    feature: Mapped[str] = mapped_column(String(100), nullable=False)
    request_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    session_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
