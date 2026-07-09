"""HTTP authorization tests for LeetCode session access."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.leetcode.dependencies import get_leetcode_service
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.main import app
from app.models.enums import AIFeature, SessionStatus
from app.services.history.history_manager import HistoryManager
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError


@pytest.fixture
def owner_id() -> UUID:
    return uuid4()


@pytest.fixture
def other_user_id() -> UUID:
    return uuid4()


@pytest.fixture
def owner(owner_id: UUID) -> AuthenticatedUser:
    return AuthenticatedUser(user_id=owner_id, email="owner@example.com", role="USER")


@pytest.fixture
def intruder(other_user_id: UUID) -> AuthenticatedUser:
    return AuthenticatedUser(user_id=other_user_id, email="other@example.com", role="USER")


def _session(owner_id: UUID) -> MagicMock:
    session = MagicMock()
    session.id = uuid4()
    session.user_id = owner_id
    session.feature = AIFeature.LEETCODE
    session.title = "Two Sum"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.model_id = None
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)
    return session


def test_history_manager_forbids_cross_user_session_access(
    owner: AuthenticatedUser,
    intruder: AuthenticatedUser,
    owner_id: UUID,
) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    session = _session(owner_id)
    session_repo.get_by_id.return_value = session

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    with pytest.raises(ForbiddenError):
        manager.get_session_detail(intruder, session.id)


def test_history_manager_delete_forbids_cross_user_access(
    owner: AuthenticatedUser,
    intruder: AuthenticatedUser,
    owner_id: UUID,
) -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    session = _session(owner_id)
    session_repo.get_by_id.return_value = session

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    with pytest.raises(ForbiddenError):
        manager.delete_session(intruder, session.id)


def test_leetcode_history_endpoint_returns_403_for_foreign_session(
    intruder: AuthenticatedUser,
    owner_id: UUID,
) -> None:
    session = _session(owner_id)
    mock_service = MagicMock()
    mock_service.get_session_detail.side_effect = ForbiddenError(
        "You do not have access to this session.",
    )

    app.dependency_overrides[require_authenticated_user] = lambda: intruder
    app.dependency_overrides[get_leetcode_service] = lambda: mock_service
    with TestClient(app) as client:
        response = client.get(
            f"/leetcode/history/{session.id}",
            headers={"Authorization": "Bearer fake-token"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 403


def test_leetcode_history_endpoint_returns_404_for_missing_session(
    intruder: AuthenticatedUser,
) -> None:
    mock_service = MagicMock()
    mock_service.get_session_detail.side_effect = RecordNotFoundError("missing")

    app.dependency_overrides[require_authenticated_user] = lambda: intruder
    app.dependency_overrides[get_leetcode_service] = lambda: mock_service
    with TestClient(app) as client:
        response = client.get(
            f"/leetcode/history/{uuid4()}",
            headers={"Authorization": "Bearer fake-token"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 404
