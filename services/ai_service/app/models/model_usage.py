"""Model usage ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base
from shared.models import CreatedAtModel

if TYPE_CHECKING:
    from app.models.ai_session import AISession


class ModelUsage(CreatedAtModel, Base):
    """Per-request LLM usage metrics stored in the AI service."""

    __tablename__ = "model_usage"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    session: Mapped[AISession] = relationship(back_populates="model_usages")
