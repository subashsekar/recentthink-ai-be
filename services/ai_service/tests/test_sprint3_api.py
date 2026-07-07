"""Sprint 3 API endpoint tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_ai_platform_service
from app.main import app
from app.models.enums import AIFeature, ModuleName, SessionStatus
from app.schemas.ai import FollowUpResponse, ModuleResponse, SummarizeResponse
from fastapi.testclient import TestClient

TEST_USER_ID = uuid4()


@pytest.fixture
def auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="user@example.com",
        role="USER",
    )


@pytest.fixture
def mock_ai_service() -> MagicMock:
    service = MagicMock()
    service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=uuid4(),
            intent="explain_again",
            teacher=ModuleResponse(
                module=ModuleName.TEACHER,
                content="Re-explained content",
            ),
            model="openai/gpt-4o-mini",
            input_tokens=50,
            output_tokens=100,
            total_tokens=150,
            latency_ms=200,
            execution_time_ms=300,
        ),
    )
    service.summarize_session = AsyncMock(
        return_value=SummarizeResponse(
            session_id=uuid4(),
            summary="Discussed two sum with hash map approach.",
            input_tokens=80,
            output_tokens=40,
            total_tokens=120,
            latency_ms=150,
            execution_time_ms=250,
        ),
    )
    service.clear_memory.return_value = None
    return service


@pytest.fixture
def client(auth_user: AuthenticatedUser, mock_ai_service: MagicMock) -> TestClient:
    app.dependency_overrides[require_authenticated_user] = lambda: auth_user
    app.dependency_overrides[get_ai_platform_service] = lambda: mock_ai_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_follow_up_endpoint(client: TestClient, mock_ai_service: MagicMock) -> None:
    session_id = uuid4()
    response = client.post(
        "/ai/follow-up",
        json={"session_id": str(session_id), "question": "Explain again"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "explain_again"
    assert body["teacher"]["module"] == "teacher"
    mock_ai_service.follow_up.assert_awaited_once()


def test_summarize_session_endpoint(client: TestClient, mock_ai_service: MagicMock) -> None:
    session_id = uuid4()
    response = client.post(
        f"/ai/session/{session_id}/summarize",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert "summary" in response.json()
    mock_ai_service.summarize_session.assert_awaited_once()


def test_clear_memory_endpoint(client: TestClient, mock_ai_service: MagicMock) -> None:
    session_id = uuid4()
    response = client.delete(
        f"/ai/memory/{session_id}",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 204
    mock_ai_service.clear_memory.assert_called_once()
