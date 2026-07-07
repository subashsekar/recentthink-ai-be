"""Agent execution trace repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_execution import AgentExecution
from app.models.enums import AgentRunStatus, ModuleName
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AgentExecutionRepository:
    """Repository for :class:`AgentExecution` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_execution(
        self,
        *,
        session_id: UUID,
        module_name: ModuleName,
        status: AgentRunStatus,
        execution_time_ms: int = 0,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        token_usage: int = 0,
        error_message: str | None = None,
        trace_metadata: dict | None = None,
    ) -> AgentExecution:
        execution = AgentExecution(
            session_id=session_id,
            module_name=module_name,
            status=status,
            execution_time_ms=execution_time_ms,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_usage=token_usage,
            error_message=error_message,
            trace_metadata=trace_metadata,
        )
        try:
            self._db.add(execution)
            self._db.commit()
            self._db.refresh(execution)
            return execution
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to create agent execution: %s", exc)
            raise RepositoryError("Failed to create execution trace.") from exc

    def list_by_session(self, session_id: UUID) -> list[AgentExecution]:
        stmt = (
            select(AgentExecution)
            .where(AgentExecution.session_id == session_id)
            .order_by(AgentExecution.created_at)
        )
        return list(self._db.scalars(stmt).all())
