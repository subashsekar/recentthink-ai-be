"""LeetCode service unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.leetcode.schemas import AnalyzeRequest, ProblemData, UpdateSessionRequest
from app.agents.leetcode.service import LeetCodeService
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, ModuleResponse, PlannerOutput
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.base import ValidationException
from shared.exceptions.repository import RecordNotFoundError


def _mock_model_registry() -> MagicMock:
    registry = MagicMock()
    registry.resolve_model_id.return_value = "google/gemini-2.5-flash"
    registry.validate_model_id.return_value = None
    return registry


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


@pytest.mark.asyncio
async def test_analyze_delegates_to_platform_service(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    platform = MagicMock()
    platform.model_registry = _mock_model_registry()
    platform.chat = AsyncMock(
        return_value=ChatResponse(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            planner=PlannerOutput(
                feature=AIFeature.LEETCODE,
                modules=[ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
                execution_mode=ExecutionMode.SINGLE_LLM,
                metadata={"difficulty": "Easy", "problem_category": "Array"},
            ),
            modules=[
                ModuleResponse(module=ModuleName.TEACHER, content="Explain."),
                ModuleResponse(module=ModuleName.CODER, content="Code", structured={}),
                ModuleResponse(
                    module=ModuleName.EVALUATOR,
                    content="Eval",
                    structured={"time_complexity": "O(n)", "space_complexity": "O(1)"},
                ),
            ],
            total_tokens=50,
            execution_time_ms=100,
        ),
    )
    session_repo = MagicMock()
    session_repo.update_session.return_value = MagicMock()
    progress_repo = MagicMock()
    fetcher = MagicMock()
    problem = ProblemData(
        title="Two Sum",
        slug="two-sum",
        url="https://leetcode.com/problems/two-sum/",
        description="desc",
        difficulty="Easy",
        topics=["Array"],
    )
    fetcher.fetch_from_url = AsyncMock(
        return_value=MagicMock(success=True, problem=problem),
    )
    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=progress_repo,
        problem_fetcher=fetcher,
    )
    response = await service.analyze(
        user,
        AnalyzeRequest(problem_url="https://leetcode.com/problems/two-sum/"),
    )
    platform.chat.assert_awaited_once()
    chat_request = platform.chat.await_args.args[1]
    assert chat_request.model == "google/gemini-2.5-flash"
    session_repo.update_session.assert_called_once()
    update_kwargs = session_repo.update_session.call_args.kwargs
    assert update_kwargs["model_id"] == "google/gemini-2.5-flash"
    assert response.session_id == session_id
    progress_repo.record_attempt.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_manual_required_creates_ai_session(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    platform = MagicMock()
    session_repo = MagicMock()
    created = MagicMock(id=session_id)
    session_repo.create_session.return_value = created
    fetcher = MagicMock()
    fetcher.fetch_from_url = AsyncMock(return_value=MagicMock(success=False, problem=None))
    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=MagicMock(),
        problem_fetcher=fetcher,
    )
    response = await service.analyze(
        user,
        AnalyzeRequest(problem_url="https://leetcode.com/problems/missing/"),
    )
    assert response.status == SessionStatus.MANUAL_REQUIRED
    platform.chat.assert_not_called()
    session_repo.create_session.assert_called_once()


def test_update_session_persists_model_id(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    existing = MagicMock()
    existing.id = session_id
    existing.user_id = user.user_id
    existing.feature = AIFeature.LEETCODE
    existing.title = "Two Sum"
    existing.status = SessionStatus.COMPLETED
    existing.model_id = None
    existing.context_metadata = {
        "title": "Two Sum",
        "slug": "two-sum",
        "url": "https://leetcode.com/problems/two-sum/",
        "difficulty": "Easy",
        "topics": ["Array"],
    }
    existing.created_at = datetime.now(UTC)
    existing.updated_at = datetime.now(UTC)

    updated = MagicMock()
    updated.id = session_id
    updated.user_id = user.user_id
    updated.feature = AIFeature.LEETCODE
    updated.title = "Two Sum"
    updated.status = SessionStatus.COMPLETED
    updated.model_id = "openai/gpt-4o"
    updated.context_metadata = existing.context_metadata
    updated.created_at = existing.created_at
    updated.updated_at = existing.updated_at

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = existing
    session_repo.update_session.return_value = updated
    platform = MagicMock()
    platform.model_registry = _mock_model_registry()
    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=MagicMock(),
    )

    result = service.update_session(
        user,
        session_id,
        UpdateSessionRequest(model_id="openai/gpt-4o"),
    )

    platform.model_registry.validate_model_id.assert_called_once_with("openai/gpt-4o")
    session_repo.update_session.assert_called_once_with(
        session_id,
        model_id="openai/gpt-4o",
    )
    assert result.model_id == "openai/gpt-4o"


def test_update_session_rejects_unknown_model(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    existing = MagicMock()
    existing.user_id = user.user_id
    existing.feature = AIFeature.LEETCODE
    session_repo = MagicMock()
    session_repo.get_by_id.return_value = existing
    platform = MagicMock()
    registry = _mock_model_registry()
    registry.validate_model_id.side_effect = ValidationException("Unknown model_id")
    platform.model_registry = registry
    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=MagicMock(),
    )

    with pytest.raises(ValidationException):
        service.update_session(
            user,
            session_id,
            UpdateSessionRequest(model_id="not-a-real-model"),
        )
    session_repo.update_session.assert_not_called()


def test_update_session_forbids_foreign_owner(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    existing = MagicMock()
    existing.user_id = uuid4()
    existing.feature = AIFeature.LEETCODE
    session_repo = MagicMock()
    session_repo.get_by_id.return_value = existing
    service = LeetCodeService(
        platform_service=MagicMock(),
        session_repo=session_repo,
        progress_repo=MagicMock(),
    )
    with pytest.raises(ForbiddenError):
        service.update_session(
            user,
            session_id,
            UpdateSessionRequest(model_id="openai/gpt-4o-mini"),
        )


def test_update_session_missing_raises_not_found(user: AuthenticatedUser) -> None:
    session_repo = MagicMock()
    session_repo.get_by_id.return_value = None
    service = LeetCodeService(
        platform_service=MagicMock(),
        session_repo=session_repo,
        progress_repo=MagicMock(),
    )
    with pytest.raises(RecordNotFoundError):
        service.update_session(
            user,
            uuid4(),
            UpdateSessionRequest(model_id="openai/gpt-4o-mini"),
        )


@pytest.mark.asyncio
async def test_follow_up_uses_session_model_when_request_omits_model(
    user: AuthenticatedUser,
) -> None:
    session_id = uuid4()
    session = MagicMock()
    session.user_id = user.user_id
    session.model_id = "openai/gpt-4o"
    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session
    platform = MagicMock()
    registry = _mock_model_registry()
    registry.resolve_model_id.return_value = "openai/gpt-4o"
    platform.model_registry = registry
    platform.follow_up = AsyncMock(
        return_value=MagicMock(
            session_id=session_id,
            intent="explain_again",
            teacher=MagicMock(content="Again."),
            input_tokens=1,
            output_tokens=2,
            total_tokens=3,
            latency_ms=4,
            execution_time_ms=5,
        ),
    )
    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=MagicMock(),
    )
    from app.agents.leetcode.schemas import FollowUpRequest

    await service.follow_up(
        user,
        FollowUpRequest(session_id=session_id, question="Explain again"),
    )
    platform.model_registry.resolve_model_id.assert_called_once_with(
        requested=None,
        session_model_id="openai/gpt-4o",
    )
    platform_request = platform.follow_up.await_args.args[1]
    assert platform_request.model == "openai/gpt-4o"
