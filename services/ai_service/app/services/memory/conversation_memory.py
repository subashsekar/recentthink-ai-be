"""Conversation memory service."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.shared.memory.engine import MemoryEngine
from app.agents.shared.memory.pruner import ContextPruner
from app.repositories.conversation_memory_repository import ConversationMemoryRepository


class ConversationMemoryService:
    """Reusable memory layer for multi-turn AI products."""

    def __init__(
        self,
        memory_repo: ConversationMemoryRepository,
        pruner: ContextPruner | None = None,
    ) -> None:
        self._repo = memory_repo
        self._engine = MemoryEngine(memory_repo, pruner=pruner)

    def load(self, session_id: UUID) -> dict[str, Any] | None:
        return self._engine.load(session_id)

    def save(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        context: dict[str, Any] | None = None,
        history_summary: str | None = None,
        previous_responses: list | None = None,
        follow_up_questions: list | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
        summary: str | None = None,
    ) -> None:
        self._engine.save_snapshot(
            session_id=session_id,
            user_id=user_id,
            context=context,
            summary=summary or history_summary,
            recent_messages=recent_messages,
            long_term=previous_responses,
            follow_up_questions=follow_up_questions,
        )

    def append_response(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        response_summary: str,
        follow_up_questions: list[str] | None = None,
        context: dict[str, Any] | None = None,
        user_message: str | None = None,
        message_type: str | None = None,
    ) -> None:
        self._engine.append_exchange(
            session_id=session_id,
            user_id=user_id,
            user_message=user_message or "",
            assistant_response=response_summary,
            context=context,
            follow_up_questions=follow_up_questions,
            message_type=message_type,
        )

    def build_prompt_context(self, session_id: UUID) -> dict[str, Any]:
        return self._engine.build_prompt_context(session_id)

    def delete(self, session_id: UUID) -> None:
        self._engine.clear(session_id)

    def get_snapshot(self, session_id: UUID) -> dict[str, Any] | None:
        record = self._repo.get_by_session_id(session_id)
        if record is None:
            return None
        return {
            "session_id": str(record.session_id),
            "summary": record.summary or record.history_summary,
            "context": record.context,
            "recent_messages": record.recent_messages,
            "previous_responses": record.previous_responses,
            "follow_up_questions": record.follow_up_questions,
            "memory_version": record.memory_version,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "updated_at": record.updated_at.isoformat() if record.updated_at else None,
        }
