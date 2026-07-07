"""Conversation memory service unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from app.services.memory.conversation_memory import ConversationMemoryService


def test_load_returns_none_when_missing() -> None:
    repo = MagicMock()
    repo.get_by_session_id.return_value = None
    service = ConversationMemoryService(repo)
    assert service.load(uuid4()) is None


def test_save_upserts_memory() -> None:
    repo = MagicMock()
    service = ConversationMemoryService(repo)
    session_id = uuid4()
    user_id = uuid4()
    service.save(session_id=session_id, user_id=user_id, context={"k": "v"})
    repo.upsert_memory.assert_called_once()


def test_append_response_merges_previous() -> None:
    repo = MagicMock()
    record = MagicMock()
    record.context = {"existing": True}
    record.previous_responses = ["old"]
    record.recent_messages = []
    record.summary = None
    record.history_summary = None
    record.follow_up_questions = None
    record.memory_version = 1
    repo.get_by_session_id.return_value = record
    service = ConversationMemoryService(repo)
    service.append_response(
        session_id=uuid4(),
        user_id=uuid4(),
        response_summary="new response",
        user_message="follow up",
    )
    repo.upsert_memory.assert_called_once()


def test_build_prompt_context() -> None:
    repo = MagicMock()
    record = MagicMock()
    record.context = {"planner_output": {"feature": "leetcode"}, "teacher_output": {"approach": "hash"}}
    record.summary = "summary"
    record.history_summary = None
    record.recent_messages = []
    record.previous_responses = []
    record.follow_up_questions = []
    record.memory_version = 1
    repo.get_by_session_id.return_value = record
    service = ConversationMemoryService(repo)
    ctx = service.build_prompt_context(uuid4())
    assert ctx.get("planner_output") is not None
    assert ctx.get("teacher_output") is not None


def test_delete_memory() -> None:
    repo = MagicMock()
    service = ConversationMemoryService(repo)
    session_id = uuid4()
    service.delete(session_id)
    repo.delete_by_session_id.assert_called_once_with(session_id)
