"""API tests for Course Generator / Learning Path endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.agents.course_generator.dependencies import get_course_generator_service
from app.agents.course_generator.schemas import (
    AdaptiveFeedbackResponse,
    AdaptiveRecommendations,
    CourseHistoryItem,
    CourseHistoryListResponse,
    CourseOverview,
    DashboardResponse,
    ExportResponse,
    FollowUpResponse,
    GenerateCourseRequest,
    GenerateCourseResponse,
    PlannerOutput,
    ProgressResponse,
    UsageSummary,
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
    app.dependency_overrides[get_course_generator_service] = lambda: mock_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sample_generate_response() -> GenerateCourseResponse:
    session_id = uuid4()
    course_id = uuid4()
    request = GenerateCourseRequest(
        skill="Python",
        goal="Become AI Engineer",
        level="Beginner",
        duration_days=60,
        daily_hours=2,
        learning_style="Hands-on",
        language="English",
        programming_language="Python",
    )
    return GenerateCourseResponse(
        session_id=session_id,
        course_id=course_id,
        status=SessionStatus.COMPLETED,
        request=request,
        planner=PlannerOutput(
            skill="Python",
            goal="Become AI Engineer",
            difficulty="Beginner",
            duration_days=60,
            daily_hours=2.0,
            estimated_study_hours=120.0,
            learning_objectives=["Build Python skills"],
            prerequisites=["Basic computer literacy"],
            roadmap_outline=["Week 1: Basics"],
            milestones=["Finish foundations"],
            execution_plan=["Analyze", "Generate"],
        ),
        overview=CourseOverview(
            title="Python to AI Engineer",
            description="A 60-day path",
            difficulty="Beginner",
            estimated_duration_days=60,
            estimated_study_hours=120,
            learning_objectives=["Learn Python"],
            prerequisites=[],
            expected_outcomes=["Build ML projects"],
        ),
        adaptive=AdaptiveRecommendations(
            struggling=["Extra practice"],
            excelling=["Unlock advanced"],
        ),
        usage=UsageSummary(total_tokens=100, execution_time_ms=50),
    )


def test_courses_generate_requires_auth() -> None:
    with TestClient(app) as unauth_client:
        resp = unauth_client.post(
            "/courses/generate",
            json={"skill": "Python", "goal": "Become AI Engineer"},
        )
    assert resp.status_code == 401


def test_courses_generate_success(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.generate = AsyncMock(return_value=_sample_generate_response())
    resp = client.post(
        "/courses/generate",
        json={
            "skill": "Python",
            "goal": "Become AI Engineer",
            "level": "Beginner",
            "duration_days": 60,
            "daily_hours": 2,
            "learning_style": "Hands-on",
            "language": "English",
            "programming_language": "Python",
        },
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["overview"]["title"] == "Python to AI Engineer"
    assert "roadmap" in body
    assert "usage" in body
    assert "execution_trace" in body


def test_courses_follow_up(client: TestClient, mock_service: MagicMock) -> None:
    session_id = uuid4()
    mock_service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session_id,
            intent="explain_again",
            teacher="Here is another explanation.",
            total_tokens=5,
            execution_time_ms=10,
        ),
    )
    resp = client.post(
        "/courses/follow-up",
        json={"session_id": str(session_id), "question": "Explain lesson again"},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["intent"] == "explain_again"


def test_courses_history(client: TestClient, mock_service: MagicMock) -> None:
    course_id = uuid4()
    session_id = uuid4()
    now = datetime.now(tz=UTC)
    mock_service.list_history.return_value = CourseHistoryListResponse(
        items=[
            CourseHistoryItem(
                course_id=course_id,
                session_id=session_id,
                title="Python Path",
                skill="Python",
                goal="AI Engineer",
                level="Beginner",
                status=SessionStatus.IN_PROGRESS,
                completion_pct=10.0,
                preview="Generate a complete course...",
                message_count=2,
                created_at=now,
                updated_at=now,
            ),
        ],
        page=1,
        page_size=50,
        total=1,
    )
    resp = client.get("/courses/history", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_courses_chat_history_list(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_history.return_value = CourseHistoryListResponse(
        items=[],
        page=1,
        page_size=50,
        total=0,
    )
    resp = client.get("/courses/chat-history", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_courses_chat_history_detail(client: TestClient, mock_service: MagicMock) -> None:
    from app.agents.course_generator.schemas import CourseChatHistoryDetailResponse

    course_id = uuid4()
    session_id = uuid4()
    now = datetime.now(tz=UTC)
    mock_service.get_chat_history.return_value = CourseChatHistoryDetailResponse(
        course_id=course_id,
        session_id=session_id,
        title="Python Path",
        skill="Python",
        goal="AI Engineer",
        level="Beginner",
        status=SessionStatus.COMPLETED,
        messages=[],
        total_messages=0,
        created_at=now,
        updated_at=now,
    )
    resp = client.get(f"/courses/chat-history/{course_id}", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["course_id"] == str(course_id)
    assert body["session_id"] == str(session_id)
    assert "messages" in body


def test_courses_delete_chat_history(client: TestClient, mock_service: MagicMock) -> None:
    course_id = uuid4()
    mock_service.delete_history.return_value = None
    resp = client.delete(
        f"/courses/chat-history/{course_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()


def test_courses_progress(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.get_progress.return_value = ProgressResponse(
        courses_created=2,
        courses_completed=1,
        lessons_completed=5,
        projects_completed=1,
        quizzes_completed=3,
        current_week=2,
        current_lesson=1,
        completion_pct=25.0,
        learning_streak=3,
        longest_streak=5,
        study_hours=12.5,
        favorite_skill="Python",
        skills=["Python"],
        updated_at=datetime.now(tz=UTC),
    )
    resp = client.get("/courses/progress", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert resp.json()["courses_created"] == 2


def test_courses_dashboard(client: TestClient, mock_service: MagicMock) -> None:
    progress = ProgressResponse(
        courses_created=1,
        courses_completed=0,
        lessons_completed=0,
        projects_completed=0,
        quizzes_completed=0,
        current_week=1,
        current_lesson=0,
        completion_pct=0.0,
        learning_streak=1,
        longest_streak=1,
        study_hours=0.0,
        skills=[],
        updated_at=datetime.now(tz=UTC),
    )
    mock_service.get_dashboard.return_value = DashboardResponse(progress=progress, recent_courses=[])
    resp = client.get("/courses/dashboard", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200
    assert "progress" in resp.json()


def test_courses_examples(client: TestClient, mock_service: MagicMock) -> None:
    mock_service.list_examples.return_value = []
    resp = client.get("/courses/examples", headers={"Authorization": "Bearer fake"})
    assert resp.status_code == 200


def test_courses_adaptive(client: TestClient, mock_service: MagicMock) -> None:
    course_id = uuid4()
    mock_service.adaptive_feedback.return_value = AdaptiveFeedbackResponse(
        course_id=course_id,
        performance="struggling",
        recommendations=["Extra practice"],
        unlock_advanced=False,
        skip_basics=False,
    )
    resp = client.post(
        "/courses/adaptive",
        json={"course_id": str(course_id), "score_pct": 40},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["performance"] == "struggling"


def test_courses_export_markdown(client: TestClient, mock_service: MagicMock) -> None:
    course_id = uuid4()
    mock_service.export.return_value = ExportResponse(
        course_id=course_id,
        format="markdown",
        filename="course.md",
        content="# Course",
        content_type="text/markdown",
    )
    resp = client.post(
        "/courses/export/markdown",
        json={"course_id": str(course_id)},
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert resp.json()["format"] == "markdown"


def test_courses_delete_history(client: TestClient, mock_service: MagicMock) -> None:
    course_id = uuid4()
    mock_service.delete_history.return_value = None
    resp = client.delete(
        f"/courses/history/{course_id}",
        headers={"Authorization": "Bearer fake"},
    )
    assert resp.status_code == 200
    assert "deleted" in resp.json()["message"].lower()
