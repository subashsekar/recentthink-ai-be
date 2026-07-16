"""Memory engine — recent, long-term, and summary layers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.agents.shared.memory.pruner import ContextPruner
from app.repositories.conversation_memory_repository import ConversationMemoryRepository
from shared.logging import get_logger

logger = get_logger(__name__)

CURRENT_MEMORY_VERSION = 1


class MemoryEngine:
    """Orchestrates recent memory, long-term memory, and conversation summaries."""

    def __init__(
        self,
        memory_repo: ConversationMemoryRepository,
        pruner: ContextPruner | None = None,
    ) -> None:
        self._memory = memory_repo
        self._pruner = pruner or ContextPruner()

    def load(self, session_id: UUID) -> dict[str, Any] | None:
        record = self._memory.get_by_session_id(session_id)
        if record is None:
            return None
        logger.info("memory_retrieved", extra={"session_id": str(session_id)})
        summary = record.summary or record.history_summary
        return {
            "context": self._pruner.prune_context(record.context),
            "summary": self._pruner.prune_summary(summary),
            "recent_messages": record.recent_messages or [],
            "long_term": record.previous_responses or [],
            "follow_up_questions": record.follow_up_questions or [],
            "memory_version": record.memory_version,
            "planner_output": (record.context or {}).get("planner_output"),
            "teacher_output": (record.context or {}).get("teacher_output"),
        }

    def save_snapshot(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        context: dict[str, Any] | None = None,
        summary: str | None = None,
        recent_messages: list[dict[str, Any]] | None = None,
        long_term: list[str] | None = None,
        follow_up_questions: list[str] | None = None,
    ) -> None:
        pruned_context = self._pruner.prune_context(context)
        pruned_recent = self._pruner.prune_recent_messages(recent_messages or [])
        pruned_summary = self._pruner.prune_summary(summary)
        self._memory.upsert_memory(
            session_id=session_id,
            user_id=user_id,
            context=pruned_context or None,
            summary=pruned_summary,
            history_summary=pruned_summary,
            recent_messages=pruned_recent or None,
            previous_responses=long_term,
            follow_up_questions=follow_up_questions,
            memory_version=CURRENT_MEMORY_VERSION,
        )

    def append_exchange(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        user_message: str,
        assistant_response: str,
        context: dict[str, Any] | None = None,
        follow_up_questions: list[str] | None = None,
        message_type: str | None = None,
    ) -> None:
        existing = self.load(session_id)
        recent = list(existing.get("recent_messages", [])) if existing else []
        timestamp = datetime.now(timezone.utc).isoformat()
        user_entry: dict[str, Any] = {
            "role": "user",
            "content": user_message,
            "timestamp": timestamp,
        }
        assistant_entry: dict[str, Any] = {
            "role": "assistant",
            "content": assistant_response,
            "timestamp": timestamp,
        }
        if message_type:
            user_entry["message_type"] = message_type
            assistant_entry["message_type"] = message_type
        recent.append(user_entry)
        recent.append(assistant_entry)
        recent = self._pruner.prune_recent_messages(recent)

        long_term = list(existing.get("long_term", [])) if existing else []
        long_term.append(assistant_response)
        long_term = long_term[-20:]

        merged_context = dict(existing.get("context", {})) if existing else {}
        if context:
            merged_context.update(context)

        summary = existing.get("summary") if existing else None
        if self._pruner.should_summarize(message_count=len(recent), recent_messages=recent):
            summary = assistant_response[:500] if not summary else summary

        self.save_snapshot(
            session_id=session_id,
            user_id=user_id,
            context=merged_context or None,
            summary=summary,
            recent_messages=recent,
            long_term=long_term,
            follow_up_questions=follow_up_questions,
        )

    def build_prompt_context(self, session_id: UUID) -> dict[str, Any]:
        memory = self.load(session_id)
        if memory is None:
            return {}
        return {
            "summary": memory.get("summary"),
            "recent_messages": memory.get("recent_messages", []),
            "planner_output": memory.get("planner_output"),
            "teacher_output": memory.get("teacher_output"),
            "context": memory.get("context"),
        }

    def clear(self, session_id: UUID) -> None:
        self._memory.delete_by_session_id(session_id)
        logger.info("memory_cleared", extra={"session_id": str(session_id)})
