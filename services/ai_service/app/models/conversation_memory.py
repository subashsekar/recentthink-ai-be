"""Conversation memory ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base
from shared.models import TimestampedModel

if TYPE_CHECKING:
    from app.models.ai_session import AISession


class ConversationMemory(TimestampedModel, Base):
    """Reusable conversation memory for multi-turn AI products."""

    __tablename__ = "conversation_memory"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    history_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recent_messages: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    previous_responses: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    follow_up_questions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    memory_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    session: Mapped[AISession] = relationship(back_populates="memory")
