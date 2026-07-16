"""Pagination and hidden-message filtering tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.services.history.history_manager import HistoryManager


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


def _message(role: MessageRole, *, metadata: dict | None = None, content: str = "msg"):
    message = MagicMock()
    message.id = uuid4()
    message.role = role
    message.module_name = ModuleName.TEACHER if role == MessageRole.ASSISTANT else None
    message.content = content
    message.content_metadata = metadata or {}
    message.created_at = datetime.now(UTC)
    return message


def test_total_messages_uses_database_count(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.user_id = user.user_id
    session.feature = AIFeature.LEETCODE
    session.title = "Session"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.model_id = None
    session.mode_id = None
    session.is_archived = False
    session.is_pinned = False
    session.last_active_at = None
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)

    visible = _message(MessageRole.USER, content="visible")
    hidden = _message(MessageRole.ASSISTANT, metadata={"status": "superseded"}, content="old")

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session
    message_repo = MagicMock()
    message_repo.list_by_session.return_value = [visible, hidden]
    message_repo.count_by_session.return_value = 42

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    detail = manager.get_session_detail(user, session_id, limit=1, offset=0)

    assert detail.total_messages == 42
    assert len(detail.messages) == 1
    assert detail.messages[0].content == "visible"


def test_include_hidden_returns_superseded_and_failed(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id
    session.user_id = user.user_id
    session.feature = AIFeature.LEETCODE
    session.title = "Session"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.model_id = None
    session.mode_id = None
    session.is_archived = False
    session.is_pinned = False
    session.last_active_at = None
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)

    failed = _message(MessageRole.ASSISTANT, metadata={"status": "failed"}, content="failed")
    deleted = _message(MessageRole.USER, metadata={"deleted": True}, content="deleted")

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session
    message_repo = MagicMock()
    message_repo.list_by_session.return_value = [failed, deleted]
    message_repo.count_by_session.return_value = 2

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    hidden = manager.get_session_detail(user, session_id, include_hidden=True)
    assert len(hidden.messages) == 2
