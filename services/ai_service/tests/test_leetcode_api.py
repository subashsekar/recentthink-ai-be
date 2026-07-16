"""API tests for LeetCode endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.leetcode.dependencies import get_leetcode_service
from app.agents.leetcode.schemas import (
    AnalyzeResponse,
    CodeExplainerOutput,
    CoderOutput,
    EvaluatorOutput,
    FollowUpResponse,
    LeetCodeHistoryItemResponse,
    LeetCodeHistoryListResponse,
    ManualInputRequiredResponse,
    PlannerOutput,
    ProblemData,
    ProgressResponse,
    SessionSummaryResponse,
    UpdateSessionRequest,
)
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.main import app
from app.models.enums import SessionStatus

TEST_USER_ID = uuid4()


@pytest.fixture
def mock_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="user@example.com",
        role="USER",
    )


@pytest.fixture
def mock_leetcode_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_user: AuthenticatedUser, mock_leetcode_service: MagicMock) -> TestClient:
    app.dependency_overrides[require_authenticated_user] = lambda: mock_user
    app.dependency_overrides[get_leetcode_service] = lambda: mock_leetcode_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_analyze_requires_auth() -> None:
    with TestClient(app) as unauth_client:
        response = unauth_client.post(
            "/leetcode/analyze",
            json={"problem_url": "https://leetcode.com/problems/two-sum/"},
        )
    assert response.status_code == 401


def test_analyze_returns_manual_required(
    client: TestClient,
    mock_leetcode_service: MagicMock,
) -> None:
    session_id = uuid4()
    mock_leetcode_service.analyze = AsyncMock(
        return_value=ManualInputRequiredResponse(
            session_id=session_id,
            status=SessionStatus.MANUAL_REQUIRED,
            message="Please paste manually.",
            instructions=["Paste statement"],
        ),
    )
    response = client.post(
        "/leetcode/analyze",
        json={"problem_url": "https://leetcode.com/problems/unknown/"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "MANUAL_REQUIRED"


def test_analyze_success(client: TestClient, mock_leetcode_service: MagicMock) -> None:
    session_id = uuid4()
    problem = ProblemData(
        title="Two Sum",
        slug="two-sum",
        url="https://leetcode.com/problems/two-sum/",
        description="Find two numbers.",
        problem_statement_markdown="### Example 1\n\n**Input:**\n\n```\nnums = [2,7]\n```",
    )
    mock_leetcode_service.analyze = AsyncMock(
        return_value=AnalyzeResponse(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            problem=problem,
            planner=PlannerOutput(
                problem_category="Array",
                difficulty="Easy",
                patterns=["Hash Map"],
                execution_plan=["Understand", "Solve"],
            ),
            teacher="Think about complements.",
            code_explainer=CodeExplainerOutput(),
            coder=CoderOutput(),
            evaluator=EvaluatorOutput(
                time_complexity="O(n)",
                space_complexity="O(n)",
                optimizations=[],
                common_mistakes=[],
                edge_cases=[],
                interview_follow_ups=["What if duplicates?"],
            ),
            total_tokens=100,
            total_execution_time_ms=500,
        ),
    )
    response = client.post(
        "/leetcode/analyze",
        json={"problem_url": "https://leetcode.com/problems/two-sum/"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()["problem"]["title"] == "Two Sum"
    assert "problem_statement_markdown" in response.json()["problem"]


def test_analyze_stream_returns_problem_statement_event(
    client: TestClient,
    mock_leetcode_service: MagicMock,
) -> None:
    session_id = uuid4()
    async def stream_events(_user, _request):
        yield (
            'data: {"type": "problem_statement", '
            '"problem_statement_markdown": "### Example 1"}\n\n'
        )
        yield (
            f'data: {{"type": "complete", "session_id": "{session_id}", '
            '"status": "COMPLETED"}}\n\n'
        )

    mock_leetcode_service.analyze_stream = stream_events
    response = client.post(
        "/leetcode/analyze?stream=true",
        json={"problem_url": "https://leetcode.com/problems/two-sum/"},
        headers={
            "Authorization": "Bearer fake-token",
            "Accept": "text/event-stream",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"type": "problem_statement"' in response.text
    assert "problem_statement_markdown" in response.text


def test_follow_up_endpoint(client: TestClient, mock_leetcode_service: MagicMock) -> None:
    session_id = uuid4()
    mock_leetcode_service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session_id,
            intent="explain_again",
            teacher="Let me explain again.",
            total_tokens=50,
            execution_time_ms=200,
        ),
    )
    response = client.post(
        "/leetcode/follow-up",
        json={"session_id": str(session_id), "question": "Explain again"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "explain_again"


def test_history_endpoint(client: TestClient, mock_leetcode_service: MagicMock) -> None:
    session_id = uuid4()
    mock_leetcode_service.list_history = MagicMock(
        return_value=LeetCodeHistoryListResponse(
            items=[
                LeetCodeHistoryItemResponse(
                    session_id=session_id,
                    title="Two Sum",
                    model_id="openai/gpt-4o-mini",
                    created_at=datetime.now(tz=UTC),
                    updated_at=datetime.now(tz=UTC),
                ),
            ],
            page=1,
            page_size=50,
            total=1,
        ),
    )
    response = client.get(
        "/leetcode/history",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["session_id"] == str(session_id)
    assert body["items"][0]["model_id"] == "openai/gpt-4o-mini"


def test_update_session_model_endpoint(
    client: TestClient,
    mock_leetcode_service: MagicMock,
) -> None:
    session_id = uuid4()
    mock_leetcode_service.update_session = MagicMock(
        return_value=SessionSummaryResponse(
            id=session_id,
            problem_title="Two Sum",
            problem_slug="two-sum",
            problem_url="https://leetcode.com/problems/two-sum/",
            difficulty="Easy",
            category="Array",
            status=SessionStatus.COMPLETED,
            model_id="google/gemini-flash-1.5",
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        ),
    )
    response = client.patch(
        f"/leetcode/history/{session_id}",
        json={"model_id": "google/gemini-flash-1.5"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()["model_id"] == "google/gemini-flash-1.5"
    mock_leetcode_service.update_session.assert_called_once()
    call_args = mock_leetcode_service.update_session.call_args.args
    assert call_args[1] == session_id
    assert isinstance(call_args[2], UpdateSessionRequest)
    assert call_args[2].model_id == "google/gemini-flash-1.5"


def test_update_session_requires_auth() -> None:
    with TestClient(app) as unauth_client:
        response = unauth_client.patch(
            f"/leetcode/history/{uuid4()}",
            json={"model_id": "openai/gpt-4o-mini"},
        )
    assert response.status_code == 401


def test_progress_endpoint(client: TestClient, mock_leetcode_service: MagicMock) -> None:
    mock_leetcode_service.get_progress = MagicMock(
        return_value=ProgressResponse(
            problems_attempted=1,
            problems_completed=1,
            easy_count=1,
            medium_count=0,
            hard_count=0,
            current_streak=1,
            longest_streak=1,
            favorite_pattern=None,
            weak_topics=[],
            strong_topics=["Array"],
            updated_at=datetime.now(tz=UTC),
        ),
    )
    response = client.get(
        "/leetcode/progress",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()["problems_completed"] == 1


def test_leetcode_versions(client: TestClient, mock_leetcode_service: MagicMock) -> None:
    from app.agents.leetcode.schemas import VersionHistoryItem

    session_id = uuid4()
    message_id = uuid4()
    mock_leetcode_service.list_versions.return_value = [
        VersionHistoryItem(
            message_id=message_id,
            created_at=datetime.now(tz=UTC),
            status="completed",
            regenerated_from_message_id=None,
            is_current=True,
        ),
    ]
    response = client.get(
        f"/leetcode/sessions/{session_id}/versions",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert response.json()[0]["message_id"] == str(message_id)
    mock_leetcode_service.list_versions.assert_called_once()
