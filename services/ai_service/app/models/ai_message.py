"""Generic AI message ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import MessageRole, ModuleName
from shared.database import Base
from shared.models import CreatedAtModel

if TYPE_CHECKING:
    from app.models.ai_session import AISession


class AIMessage(CreatedAtModel, Base):
    """Persisted message in an AI session."""

    __tablename__ = "ai_messages"

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
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="ai_message_role", native_enum=False, length=50),
        nullable=False,
    )
    module_name: Mapped[ModuleName | None] = mapped_column(
        Enum(ModuleName, name="ai_module_name", native_enum=False, length=50),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    session: Mapped[AISession] = relationship(back_populates="messages")
