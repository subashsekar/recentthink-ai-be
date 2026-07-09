"""History manager unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, SessionStatus
from app.services.history.history_manager import HistoryManager
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


@pytest.fixture
def admin() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="a@example.com", role="ADMIN")


def _session(owner_id: UUID) -> MagicMock:
    session = MagicMock()
    session.id = uuid4()
    session.user_id = owner_id
    session.feature = AIFeature.LEETCODE
    session.title = "Session"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.model_id = None
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)
    return session


def test_list_history_for_user(user: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    session = _session(user.user_id)
    session_repo.list_by_user.return_value = [session]
    session_repo.count_by_user.return_value = 1

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    result = manager.list_history(user)
    assert result.total == 1
    assert len(result.sessions) == 1


def test_get_session_detail_forbidden(user: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    other_session = _session(uuid4())
    session_repo.get_by_id.return_value = other_session

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    with pytest.raises(ForbiddenError):
        manager.get_session_detail(user, other_session.id)


def test_get_session_detail_not_found(user: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    session_repo.get_by_id.return_value = None

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    with pytest.raises(RecordNotFoundError):
        manager.get_session_detail(user, uuid4())


def test_admin_can_access_any_session(admin: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    owner_id = uuid4()
    session = _session(owner_id)
    session_repo.get_by_id.return_value = session
    message_repo.list_by_session.return_value = []

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    result = manager.get_session_detail(admin, session.id)
    assert result.session.id == session.id


def test_get_session_detail_includes_memory(user: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    memory_repo = MagicMock()
    session = _session(user.user_id)
    session_repo.get_by_id.return_value = session
    message_repo.list_by_session.return_value = []

    memory = MagicMock()
    memory.session_id = session.id
    memory.summary = "Discussed two sum"
    memory.history_summary = None
    memory.context = {"planner_output": {"feature": "leetcode"}}
    memory.recent_messages = [{"role": "user", "content": "hi"}]
    memory.previous_responses = ["response"]
    memory.follow_up_questions = ["What next?"]
    memory.memory_version = 1
    memory.created_at = datetime.now(UTC)
    memory.updated_at = datetime.now(UTC)
    memory_repo.get_by_session_id.return_value = memory

    manager = HistoryManager(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_repo=memory_repo,
    )
    result = manager.get_session_detail(user, session.id)
    assert result.memory is not None
    assert result.memory.summary == "Discussed two sum"
    assert result.memory.memory_version == 1
