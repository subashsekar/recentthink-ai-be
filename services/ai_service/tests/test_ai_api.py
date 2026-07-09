"""AI API tests with dependency overrides."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_ai_platform_service
from app.main import app
from app.models.enums import AIFeature, ExecutionMode, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import (
    ChatResponse,
    HistoryListResponse,
    ModelInfo,
    ModelsResponse,
    ModuleResponse,
    PlannerOutput,
    SessionDetailResponse,
    SessionSummaryResponse,
)
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
    service.chat = AsyncMock(
        return_value=ChatResponse(
            session_id=uuid4(),
            status=SessionStatus.COMPLETED,
            planner=PlannerOutput(
                feature=AIFeature.LEETCODE,
                modules=[ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
                execution_mode=ExecutionMode.SINGLE_LLM,
            ),
            modules=[
                ModuleResponse(
                    module=ModuleName.TEACHER,
                    content="Explanation",
                ),
            ],
            model="openai/gpt-4o-mini",
            provider="openai",
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            latency_ms=500,
            execution_time_ms=800,
            estimated_cost=0.001,
        ),
    )
    service.list_history.return_value = HistoryListResponse(
        sessions=[],
        total=0,
        limit=50,
        offset=0,
    )
    service.get_session_detail.return_value = SessionDetailResponse(
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
    service.delete_session.return_value = None
    service.list_models.return_value = ModelsResponse(
        models=[
            ModelInfo(
                id="google/gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                provider="Google",
                description="Fast",
                recommended=True,
                default=True,
                enabled=True,
            ),
        ],
        default_model="google/gemini-2.5-flash",
    )
    return service


@pytest.fixture
def client(auth_user: AuthenticatedUser, mock_ai_service: MagicMock) -> TestClient:
    app.dependency_overrides[require_authenticated_user] = lambda: auth_user
    app.dependency_overrides[get_ai_platform_service] = lambda: mock_ai_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_chat_endpoint(client: TestClient, mock_ai_service: MagicMock) -> None:
    response = client.post(
        "/ai/chat",
        json={"feature": "leetcode", "message": "Explain two sum"},
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["planner"]["feature"] == "leetcode"
    mock_ai_service.chat.assert_awaited_once()


def test_list_history(client: TestClient) -> None:
    response = client.get(
        "/ai/history",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_get_session_history(client: TestClient) -> None:
    session_id = uuid4()
    response = client.get(
        f"/ai/history/{session_id}",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert "session" in response.json()


def test_delete_session_history(client: TestClient, mock_ai_service: MagicMock) -> None:
    session_id = uuid4()
    response = client.delete(
        f"/ai/history/{session_id}",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 204
    mock_ai_service.delete_session.assert_called_once()


def test_list_models(client: TestClient) -> None:
    response = client.get(
        "/ai/models",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.json()["default_model"] == "google/gemini-2.5-flash"
    assert response.json()["models"][0]["name"] == "Gemini 2.5 Flash"
