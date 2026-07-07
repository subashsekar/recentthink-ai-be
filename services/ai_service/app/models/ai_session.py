"""Generic AI session ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import AIFeature, SessionStatus
from shared.database import Base
from shared.models import TimestampedModel

if TYPE_CHECKING:
    from app.models.agent_execution import AgentExecution
    from app.models.ai_message import AIMessage
    from app.models.conversation_memory import ConversationMemory
    from app.models.model_usage import ModelUsage


class AISession(TimestampedModel, Base):
    """A reusable AI conversation session for any product feature."""

    __tablename__ = "ai_sessions"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    feature: Mapped[AIFeature] = mapped_column(
        Enum(AIFeature, name="ai_feature", native_enum=False, length=50),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="ai_session_status", native_enum=False, length=50),
        default=SessionStatus.PENDING,
        server_default=SessionStatus.PENDING.value,
        nullable=False,
    )
    context_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    messages: Mapped[list[AIMessage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AIMessage.created_at",
    )
    executions: Mapped[list[AgentExecution]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="AgentExecution.created_at",
    )
    memory: Mapped[ConversationMemory | None] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )
    model_usages: Mapped[list[ModelUsage]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ModelUsage.created_at",
    )
