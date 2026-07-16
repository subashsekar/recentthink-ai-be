"""Chat API route tests with dependency overrides."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_chat_service
from app.main import app
from app.models.enums import AIFeature, SessionStatus
from app.models.enums import AIFeature, ModuleName
from app.schemas.ai import FollowUpResponse, HistoryListResponse, ModuleResponse, SessionDetailResponse, SessionSummaryResponse
from app.services.chat.schemas import ChatActionResponse, ChatExportResponse, ExportFormat, ExportType
from fastapi.testclient import TestClient

TEST_USER_ID = uuid4()


@pytest.fixture
def auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=TEST_USER_ID, email="user@example.com", role="USER")


@pytest.fixture
def mock_chat_service() -> MagicMock:
    service = MagicMock()
    service.list_sessions.return_value = HistoryListResponse(
        sessions=[],
        total=0,
        limit=50,
        offset=0,
    )
    service.get_session.return_value = SessionDetailResponse(
        session=SessionSummaryResponse(
            id=uuid4(),
            feature=AIFeature.LEETCODE,
            title="Test",
            status=SessionStatus.COMPLETED,
            summary=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        ),
        messages=[],
        total_messages=0,
    )
    service.export_session.return_value = ChatExportResponse(
        session_id=uuid4(),
        format=ExportFormat.MARKDOWN,
        export_type=ExportType.CONVERSATION,
        filename="conversation.md",
        content="# Conversation Export\n",
        content_type="text/markdown",
    )
    service.continue_response = AsyncMock(
        return_value=ChatActionResponse(session_id=uuid4(), message_id=uuid4(), action="continue", response=None),
    )
    service.retry_response = AsyncMock(
        return_value=ChatActionResponse(session_id=uuid4(), message_id=uuid4(), action="retry", response=None),
    )
    service.regenerate_response = AsyncMock(
        return_value=ChatActionResponse(session_id=uuid4(), message_id=uuid4(), action="regenerate", response=None),
    )
    service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=uuid4(),
            intent="explain_again",
            teacher=ModuleResponse(module=ModuleName.TEACHER, content="Follow-up"),
            model="openai/gpt-4o-mini",
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            latency_ms=1,
            execution_time_ms=1,
        ),
    )
    service.rename_session.return_value = service.get_session.return_value.session
    service.archive_session.return_value = service.get_session.return_value.session
    service.pin_session.return_value = service.get_session.return_value.session
    service.delete_session.return_value = None
    service.bookmark_message.return_value = {"bookmarked": True}
    service.delete_message.return_value = None

    async def stream_frames(*_args, **_kwargs):
        yield 'data: {"type":"done"}\n\n'

    service.stream = stream_frames
    return service


@pytest.fixture
def client(auth_user: AuthenticatedUser, mock_chat_service: MagicMock) -> TestClient:
    app.dependency_overrides[require_authenticated_user] = lambda: auth_user
    app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_list_chat_sessions(client: TestClient, mock_chat_service: MagicMock) -> None:
    response = client.get("/chat/leetcode/sessions")
    assert response.status_code == 200
    assert response.json()["total"] == 0
    mock_chat_service.list_sessions.assert_called_once()


def test_export_chat_session(client: TestClient, mock_chat_service: MagicMock) -> None:
    session_id = str(uuid4())
    response = client.post(
        f"/chat/leetcode/export",
        json={
            "session_id": session_id,
            "format": "markdown",
            "export_type": "conversation",
        },
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "conversation.md"
    mock_chat_service.export_session.assert_called_once()


def test_chat_stream_endpoint(client: TestClient) -> None:
    response = client.post(
        "/chat/leetcode/stream",
        json={"message": "Solve two sum"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_continue_retry_regenerate_follow_up_routes(client: TestClient, mock_chat_service: MagicMock) -> None:
    session_id = str(uuid4())
    message_id = str(uuid4())

    continue_resp = client.post(
        "/chat/leetcode/continue",
        json={"session_id": session_id},
    )
    assert continue_resp.status_code == 200
    mock_chat_service.continue_response.assert_awaited_once()

    retry_resp = client.post(
        "/chat/leetcode/retry",
        json={"session_id": session_id, "message_id": message_id},
    )
    assert retry_resp.status_code == 200
    mock_chat_service.retry_response.assert_awaited_once()

    regen_resp = client.post(
        "/chat/leetcode/regenerate",
        json={"session_id": session_id, "message_id": message_id},
    )
    assert regen_resp.status_code == 200
    mock_chat_service.regenerate_response.assert_awaited_once()

    follow_resp = client.post(
        "/chat/leetcode/follow-up",
        json={"session_id": session_id, "question": "Explain again"},
    )
    assert follow_resp.status_code == 200
    mock_chat_service.follow_up.assert_awaited_once()


def test_session_management_and_message_routes(client: TestClient, mock_chat_service: MagicMock) -> None:
    session_id = str(uuid4())
    message_id = str(uuid4())

    rename = client.patch(
        f"/chat/leetcode/sessions/{session_id}/rename",
        json={"title": "Renamed"},
    )
    assert rename.status_code == 200

    archive = client.patch(
        f"/chat/leetcode/sessions/{session_id}/archive",
        json={"archived": True},
    )
    assert archive.status_code == 200

    pin = client.patch(
        f"/chat/leetcode/sessions/{session_id}/pin",
        json={"pinned": True},
    )
    assert pin.status_code == 200

    delete_session = client.delete(f"/chat/leetcode/sessions/{session_id}")
    assert delete_session.status_code == 204

    bookmark = client.patch(
        f"/chat/leetcode/messages/{message_id}/bookmark",
        json={"bookmarked": True},
    )
    assert bookmark.status_code == 200

    delete_message = client.delete(f"/chat/leetcode/messages/{message_id}")
    assert delete_message.status_code == 204


def test_get_session_include_hidden_query(client: TestClient, mock_chat_service: MagicMock) -> None:
    session_id = str(uuid4())
    response = client.get(f"/chat/leetcode/sessions/{session_id}?include_hidden=true")
    assert response.status_code == 200
    mock_chat_service.get_session.assert_called_once()
    assert mock_chat_service.get_session.call_args.kwargs["include_hidden"] is True


def test_interview_chat_stream_returns_501(client: TestClient, mock_chat_service: MagicMock) -> None:
    response = client.post(
        "/chat/interview/stream",
        json={"message": "Practice a system design interview"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 501
    assert "Interview Trainer" in response.json()["detail"]
