"""LeetCode service unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.leetcode.schemas import AnalyzeRequest, ProblemData
from app.agents.leetcode.service import LeetCodeService
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, ModuleResponse, PlannerOutput


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


@pytest.mark.asyncio
async def test_analyze_delegates_to_platform_service(user: AuthenticatedUser) -> None:
    session_id = uuid4()
    platform = MagicMock()
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
