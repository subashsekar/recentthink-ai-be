"""API tests for DSA Pattern Coach endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.dsa_pattern.dependencies import get_dsa_pattern_service
from app.agents.dsa_pattern.schemas import (
    DashboardResponse,
    ExportResponse,
    FollowUpResponse,
    GeneratePatternRequest,
    GeneratePatternResponse,
    InterviewTips,
    MentalModel,
    NextPatternRecommendation,
    PatternHistoryItem,
    PatternHistoryListResponse,
    PatternOverview,
    PlannerOutput,
    PracticeContent,
    ProgressResponse,
    QuizContent,
    RecognitionGuide,
    UsageSummary,
    VisualizationContent,
    WalkthroughExample,
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
    app.dependency_overrides[get_dsa_pattern_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sample_generate_response() -> GeneratePatternResponse:
    session_id = uuid4()
    pattern_session_id = uuid4()
    request = GeneratePatternRequest(
        pattern="Sliding Window",
        level="Beginner",
        language="Python",
        learning_style="Visual",
    )
    return GeneratePatternResponse(
        session_id=session_id,
        pattern_session_id=pattern_session_id,
        status=SessionStatus.COMPLETED,
        request=request,
        planner=PlannerOutput(
            pattern="Sliding Window",
            category="Sliding Window",
            difficulty="Beginner",
            prerequisites=["Arrays"],
            estimated_study_time="4–6 hours",
            learning_objectives=["Recognize sliding window"],
            roadmap=["Day 1: Overview"],
            execution_plan=["Plan", "Generate"],
        ),
        overview=PatternOverview(
            pattern="Sliding Window",
            definition="Maintain a contiguous window over an array/string.",
            category="Array",
            difficulty="Beginner",
            learning_objectives=["Identify window problems"],
        ),
        mental_model=MentalModel(summary="A moving frame over contiguous data", analogies=["Telescope"]),
        recognition=RecognitionGuide(
            keywords=["subarray", "substring", "window"],
            checklist=["Is the answer contiguous?"],
            how_to_identify="Look for contiguous subarray/substring constraints.",
        ),
        visualization=VisualizationContent(ascii_diagrams=["[L----R]"], step_by_step=["expand R", "shrink L"]),
        templates=[],
        easy_example=WalkthroughExample(difficulty="easy", title="Max Sum Subarray of Size K"),
        medium_example=WalkthroughExample(difficulty="medium", title="Longest Substring Without Repeating"),
        hard_example=WalkthroughExample(difficulty="hard", title="Minimum Window Substring"),
        common_mistakes=["Forgetting to shrink the window"],
        interview_tips=InterviewTips(interview_questions=["When do you expand vs shrink?"]),
        pattern_comparison=[],
        practice=PracticeContent(roadmap=["Start with fixed window"]),
        quiz=QuizContent(title="Sliding Window Quiz"),
        next_pattern_recommendation=NextPatternRecommendation(
            pattern="Two Pointers",
            reason="Natural follow-up for contiguous scans",
        ),
        usage=UsageSummary(total_tokens=100, execution_time_ms=50),
    )


def test_dsa_pattern_generate_requires_auth() -> None:
    with TestClient(app) as unauth_client:
        resp = unauth_client.post(
            "/dsa-pattern/generate",
            json={"pattern": "Sliding Window", "level": "Beginner", "language": "Python"},
        )
    assert resp.status_code == 401


def test_dsa_pattern_generate_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.generate = AsyncMock(return_value=_sample_generate_response())
    resp = client.post(
        "/dsa-pattern/generate",
        json={
            "pattern": "Sliding Window",
            "level": "Beginner",
            "language": "Python",
            "learning_style": "Visual",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overview"]["pattern"] == "Sliding Window"
    assert body["recognition"]["keywords"]
    assert "session_id" in body
    assert "pattern_session_id" in body
    mock_service.generate.assert_awaited_once()


def test_dsa_pattern_generate_validation(client: TestClient) -> None:
    resp = client.post("/dsa-pattern/generate", json={"level": "Beginner"})
    assert resp.status_code == 422


def test_dsa_pattern_follow_up(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session_id,
            intent="explain_again",
            teacher="Here is another explanation...",
        ),
    )
    resp = client.post(
        "/dsa-pattern/follow-up",
        json={"session_id": str(session_id), "question": "Explain again with another analogy"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "explain_again"


def test_dsa_pattern_history(client: TestClient, mock_service: MagicMock) -> None:
    now = datetime.now(tz=UTC)
    mock_service.list_history.return_value = PatternHistoryListResponse(
        items=[
            PatternHistoryItem(
                pattern_session_id=uuid4(),
                session_id=uuid4(),
                title="Sliding Window Pattern Coach",
                pattern="Sliding Window",
                level="Beginner",
                status=SessionStatus.COMPLETED,
                created_at=now,
                updated_at=now,
            ),
        ],
        page=1,
        page_size=50,
        total=1,
    )
    resp = client.get("/dsa-pattern/history")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_dsa_pattern_progress(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_progress.return_value = ProgressResponse(
        patterns_learned=2,
        patterns_mastered=1,
        practice_completed=5,
        quizzes_completed=2,
        average_quiz_score=80.0,
        current_streak=3,
        longest_streak=5,
        learning_time_minutes=120,
        recommended_next_pattern="Two Pointers",
        weak_patterns=["DP"],
        strong_patterns=["Sliding Window"],
        patterns=["Sliding Window", "Binary Search"],
        updated_at=datetime.now(tz=UTC),
    )
    resp = client.get("/dsa-pattern/progress")
    assert resp.status_code == 200
    assert resp.json()["patterns_learned"] == 2


def test_dsa_pattern_dashboard(client: TestClient, mock_service: MagicMock) -> None:
    progress = ProgressResponse(
        patterns_learned=1,
        patterns_mastered=0,
        practice_completed=0,
        quizzes_completed=0,
        average_quiz_score=0.0,
        current_streak=1,
        longest_streak=1,
        learning_time_minutes=0,
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.get_dashboard.return_value = DashboardResponse(progress=progress, recent_sessions=[])
    resp = client.get("/dsa-pattern/dashboard")
    assert resp.status_code == 200
    assert resp.json()["progress"]["patterns_learned"] == 1


def test_dsa_pattern_examples(client: TestClient, mock_service: MagicMock) -> None:
    from app.agents.dsa_pattern.schemas import PatternExampleResponse

    mock_service.list_examples.return_value = [
        PatternExampleResponse(
            id="sliding-window",
            title="Sliding Window",
            pattern="Sliding Window",
            level="Beginner",
            language="Python",
            learning_style="Visual",
        ),
    ]
    resp = client.get("/dsa-pattern/examples")
    assert resp.status_code == 200
    assert resp.json()[0]["pattern"] == "Sliding Window"


def test_dsa_pattern_export_markdown(client: TestClient, mock_service: MagicMock) -> None:
    pattern_session_id = uuid4()
    mock_service.export.return_value = ExportResponse(
        pattern_session_id=pattern_session_id,
        format="markdown",
        filename="Sliding_Window.md",
        content="# Sliding Window",
        content_type="text/markdown",
    )
    resp = client.post(
        "/dsa-pattern/export/markdown",
        json={"pattern_session_id": str(pattern_session_id)},
    )
    assert resp.status_code == 200
    assert resp.json()["format"] == "markdown"


def test_dsa_pattern_delete_history(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.delete_history.return_value = None
    resp = client.delete(f"/dsa-pattern/history/{session_id}")
    assert resp.status_code == 200
    mock_service.delete_history.assert_called_once()


def test_dsa_pattern_versions(client: TestClient, mock_service: MagicMock) -> None:
    from app.agents.dsa_pattern.schemas import VersionHistoryItem

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
    resp = client.get(f"/dsa-pattern/sessions/{session_id}/versions")
    assert resp.status_code == 200
    assert resp.json()[0]["is_current"] is True
    mock_service.list_versions.assert_called_once()
