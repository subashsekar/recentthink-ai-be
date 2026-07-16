"""API tests for HackerRank endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.hackerrank.dependencies import get_hackerrank_service
from app.agents.hackerrank.schemas import (
    AnalyzeResponse,
    CodeExplainerOutput,
    CoderOutput,
    EvaluatorOutput,
    FollowUpResponse,
    HackerrankHistoryItemResponse,
    HackerrankHistoryListResponse,
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
    return AuthenticatedUser(user_id=TEST_USER_ID, email="user@example.com", role="USER")


@pytest.fixture
def mock_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(mock_user: AuthenticatedUser, mock_service: MagicMock) -> TestClient:
    app.dependency_overrides[require_authenticated_user] = lambda: mock_user
    app.dependency_overrides[get_hackerrank_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_hackerrank_analyze_requires_auth() -> None:
    with TestClient(app) as unauth_client:
        resp = unauth_client.post(
            "/hackerrank/analyze",
            json={"problem_url": "https://www.hackerrank.com/challenges/solve-me-first/problem"},
        )
    assert resp.status_code == 401


def test_hackerrank_analyze_manual_required(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.analyze = AsyncMock(
        return_value=ManualInputRequiredResponse(
            session_id=session_id,
            status=SessionStatus.MANUAL_REQUIRED,
            message="Paste manually.",
            instructions=["Paste statement"],
        ),
    )
    resp = client.post(
        "/hackerrank/analyze",
        json={"problem_url": "https://www.hackerrank.com/challenges/unknown/problem"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "MANUAL_REQUIRED"


def test_hackerrank_analyze_success(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    problem = ProblemData(
        title="Solve Me First",
        slug="solve-me-first",
        url="https://www.hackerrank.com/challenges/solve-me-first/problem",
        description="Add two numbers.",
        problem_statement_markdown="Add two numbers.",
        domain="Algorithms",
    )
    mock_service.analyze = AsyncMock(
        return_value=AnalyzeResponse(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            problem=problem,
            planner=PlannerOutput(
                problem_category="Algorithms",
                difficulty="Easy",
                patterns=["Array"],
                execution_plan=["Understand", "Solve"],
                problem_domain="Algorithms",
                learning_objectives=["Recognize patterns"],
            ),
            teacher="Focus on input/output.",
            code_explainer=CodeExplainerOutput(),
            coder=CoderOutput(),
            evaluator=EvaluatorOutput(
                time_complexity="O(1)",
                space_complexity="O(1)",
                optimizations=[],
                common_mistakes=[],
                edge_cases=[],
                interview_follow_ups=[],
            ),
            total_tokens=10,
            total_execution_time_ms=50,
        ),
    )
    resp = client.post(
        "/hackerrank/analyze",
        json={"problem_url": "https://www.hackerrank.com/challenges/solve-me-first/problem"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["problem"]["slug"] == "solve-me-first"
    assert "code_explainer" in resp.json()


def test_hackerrank_follow_up(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session_id,
            intent="explain_again",
            teacher="Sure.",
            total_tokens=5,
            execution_time_ms=10,
        ),
    )
    resp = client.post(
        "/hackerrank/follow-up",
        json={"session_id": str(session_id), "question": "Explain again"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "explain_again"


def test_hackerrank_history(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.list_history = MagicMock(
        return_value=HackerrankHistoryListResponse(
            items=[
                HackerrankHistoryItemResponse(
                    session_id=session_id,
                    title="Solve Me First",
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
    resp = client.get("/hackerrank/history", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["items"][0]["session_id"] == str(session_id)


def test_hackerrank_update_session(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.update_session = MagicMock(
        return_value=SessionSummaryResponse(
            id=session_id,
            problem_title="Solve Me First",
            problem_slug="solve-me-first",
            problem_url="https://www.hackerrank.com/challenges/solve-me-first/problem",
            difficulty="Easy",
            category="Algorithms",
            status=SessionStatus.COMPLETED,
            model_id="google/gemini-flash-1.5",
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
        ),
    )
    resp = client.patch(
        f"/hackerrank/history/{session_id}",
        json={"model_id": "google/gemini-flash-1.5"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    mock_service.update_session.assert_called_once()
    args = mock_service.update_session.call_args.args
    assert args[1] == session_id
    assert isinstance(args[2], UpdateSessionRequest)


def test_hackerrank_progress(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_progress = MagicMock(
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
            strong_topics=["Algorithms"],
            updated_at=datetime.now(tz=UTC),
        ),
    )
    resp = client.get("/hackerrank/progress", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["problems_completed"] == 1



def test_hackerrank_modes(client: TestClient, mock_service: MagicMock) -> None:
    from app.agents.hackerrank.schemas import HackerrankModeResponse

    mock_service.list_modes.return_value = [
        HackerrankModeResponse(
            id="learning",
            label="Learning",
            description="Step-by-step coaching",
            icon="book",
            recommended=True,
        ),
    ]
    resp = client.get("/hackerrank/modes", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "learning"
    mock_service.list_modes.assert_called_once()


def test_hackerrank_versions(client: TestClient, mock_service: MagicMock) -> None:
    from app.agents.hackerrank.schemas import VersionHistoryItem

    session_id = uuid4()
    message_id = uuid4()
    mock_service.list_versions.return_value = [
        VersionHistoryItem(
            message_id=message_id,
            created_at=datetime.now(tz=UTC),
            status="completed",
            regenerated_from_message_id=None,
            is_current=True,
        ),
    ]
    resp = client.get(
        f"/hackerrank/sessions/{session_id}/versions",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()[0]["message_id"] == str(message_id)
    mock_service.list_versions.assert_called_once()
