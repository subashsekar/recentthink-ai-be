"""Integration tests for the LeetCode analyze workflow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.leetcode.schemas import AnalyzeRequest
from app.agents.leetcode.service import LeetCodeService
from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.clients.openrouter import LLMResponse
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatRequest, ChatResponse, ModuleResponse, PlannerOutput


@pytest.mark.asyncio
async def test_leetcode_service_analyze_integrates_with_platform_workflow() -> None:
    """LeetCodeService delegates analyze to the shared platform and maps the response."""
    user = AuthenticatedUser(user_id=uuid4(), email="user@example.com", role="USER")
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
                metadata={
                    "difficulty": "Easy",
                    "problem_category": "Array",
                    "patterns": ["Hash Map"],
                },
            ),
            modules=[
                ModuleResponse(
                    module=ModuleName.TEACHER,
                    content="Think about complements.",
                    structured={"approach": "hash map"},
                ),
                ModuleResponse(
                    module=ModuleName.CODER,
                    content="```python\ndef two_sum(nums, target): pass\n```",
                    structured={
                        "brute_force": {"code": "def bf(): pass"},
                        "better_solution": {"code": "def better(): pass"},
                        "optimal_solution": {"code": "def opt(): pass"},
                    },
                ),
                ModuleResponse(
                    module=ModuleName.EVALUATOR,
                    content="Time: O(n)",
                    structured={
                        "time_complexity": "O(n)",
                        "space_complexity": "O(n)",
                        "follow_up_questions": ["sorted input?"],
                    },
                ),
            ],
            model="openai/gpt-4o-mini",
            provider="openai",
            input_tokens=100,
            output_tokens=200,
            total_tokens=300,
            latency_ms=150,
            execution_time_ms=400,
            estimated_cost=0.001,
        ),
    )

    session_repo = MagicMock()
    progress_repo = MagicMock()

    service = LeetCodeService(
        platform_service=platform,
        session_repo=session_repo,
        progress_repo=progress_repo,
    )

    response = await service.analyze(
        user,
        AnalyzeRequest(
            title="Two Sum",
            problem_statement="Given an array of integers, return indices of the two numbers.",
        ),
    )

    platform.chat.assert_awaited_once()
    chat_request: ChatRequest = platform.chat.await_args.args[1]
    assert chat_request.feature == AIFeature.LEETCODE
    assert chat_request.context is not None
    assert chat_request.context["title"] == "Two Sum"

    session_repo.update_session.assert_called_once()
    progress_repo.record_attempt.assert_called_once_with(
        user.user_id,
        difficulty="Easy",
        category="Array",
        completed=True,
    )

    assert response.session_id == session_id
    assert response.planner.difficulty == "Easy"
    assert response.coder.optimal is not None
    assert response.evaluator.time_complexity == "O(n)"


@pytest.mark.asyncio
async def test_platform_orchestrator_end_to_end_with_mocked_llm() -> None:
    """Full shared workflow executes through the orchestrator for a LeetCode request."""
    user_id = uuid4()
    session = MagicMock()
    session.id = uuid4()

    session_repo = MagicMock()
    session_repo.create_session.return_value = session
    session_repo.update_session.return_value = session

    llm = MagicMock()
    llm.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content=(
                '{"teacher":{"thinking_process":"use a map","concepts":["Hash Map"],'
                '"approach":"store complements"},'
                '"coder":{"brute_force":{"language":"python","code":"def bf(): pass"},'
                '"better_solution":{"language":"python","code":"def better(): pass"},'
                '"optimal_solution":{"language":"python","code":"def opt(): pass","complexity":"O(n)"}},'
                '"evaluator":{"time_complexity":"O(n)","space_complexity":"O(n)",'
                '"follow_up_questions":["sorted input?"],"edge_cases":["empty"]}}'
            ),
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=40,
            completion_tokens=80,
            latency_ms=120,
            estimated_cost=0.0004,
        ),
    )

    usage_client = MagicMock()
    usage_client.record_usage = AsyncMock()

    from app.services.usage.usage_tracker import UsageTracker

    orchestrator = AIPlatformOrchestrator(
        llm_client=llm,
        prompt_loader=MagicMock(load=MagicMock(return_value="system prompt")),
        session_repo=session_repo,
        message_repo=MagicMock(),
        execution_trace=MagicMock(record=MagicMock()),
        memory_service=MagicMock(
            build_prompt_context=MagicMock(return_value={}),
            append_response=MagicMock(),
        ),
        usage_tracker=UsageTracker(usage_client=usage_client, model_usage_repo=MagicMock()),
    )

    result = await orchestrator.execute(
        user_id=user_id,
        request=ChatRequest(
            feature=AIFeature.LEETCODE,
            message="Analyze two sum",
            title="Two Sum",
            context={"title": "Two Sum", "difficulty": "Easy"},
        ),
    )

    assert result.status == SessionStatus.COMPLETED
    assert len(result.modules) == 4
    assert result.total_tokens == 120
    llm.chat_completion.assert_awaited_once()
    usage_client.record_usage.assert_awaited_once()
