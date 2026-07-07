"""Agent execution trace ORM model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.enums import AgentRunStatus, ModuleName
from shared.database import Base
from shared.models import CreatedAtModel

if TYPE_CHECKING:
    from app.models.ai_session import AISession


class AgentExecution(CreatedAtModel, Base):
    """Execution trace for planner, LLM, and processing modules."""

    __tablename__ = "agent_execution"

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
    module_name: Mapped[ModuleName] = mapped_column(
        Enum(ModuleName, name="agent_execution_module", native_enum=False, length=50),
        nullable=False,
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_execution_status", native_enum=False, length=50),
        default=AgentRunStatus.SUCCESS,
        nullable=False,
    )
    execution_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    trace_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    session: Mapped[AISession] = relationship(back_populates="executions")
