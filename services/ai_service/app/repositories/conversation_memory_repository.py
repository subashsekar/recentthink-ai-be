"""Conversation memory repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation_memory import ConversationMemory
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class ConversationMemoryRepository:
    """Repository for :class:`ConversationMemory` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_session_id(self, session_id: UUID) -> ConversationMemory | None:
        return (
            self._db.query(ConversationMemory)
            .filter(ConversationMemory.session_id == session_id)
            .one_or_none()
        )

    def upsert_memory(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        context: dict | None = None,
        summary: str | None = None,
        history_summary: str | None = None,
        recent_messages: list | None = None,
        previous_responses: list | None = None,
        follow_up_questions: list | None = None,
        memory_version: int | None = None,
    ) -> ConversationMemory:
        memory = self.get_by_session_id(session_id)
        if memory is None:
            memory = ConversationMemory(
                session_id=session_id,
                user_id=user_id,
                context=context,
                summary=summary,
                history_summary=history_summary or summary,
                recent_messages=recent_messages,
                previous_responses=previous_responses,
                follow_up_questions=follow_up_questions,
                memory_version=memory_version or 1,
            )
            self._db.add(memory)
        else:
            if context is not None:
                memory.context = context
            if summary is not None:
                memory.summary = summary
                memory.history_summary = summary
            elif history_summary is not None:
                memory.history_summary = history_summary
                if memory.summary is None:
                    memory.summary = history_summary
            if recent_messages is not None:
                memory.recent_messages = recent_messages
            if previous_responses is not None:
                memory.previous_responses = previous_responses
            if follow_up_questions is not None:
                memory.follow_up_questions = follow_up_questions
            if memory_version is not None:
                memory.memory_version = memory_version
        try:
            self._db.commit()
            self._db.refresh(memory)
            return memory
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to upsert conversation memory: %s", exc)
            raise RepositoryError("Failed to save conversation memory.") from exc

    def delete_by_session_id(self, session_id: UUID) -> None:
        memory = self.get_by_session_id(session_id)
        if memory is None:
            raise RecordNotFoundError(f"Memory for session '{session_id}' not found.")
        try:
            self._db.delete(memory)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to delete conversation memory.") from exc
