"""LangGraph workflow engine tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.teacher.module import TeacherModule
from app.agents.shared.workflow.graph import AIWorkflowEngine
from app.agents.shared.workflow.nodes import WorkflowNodes
from app.clients.openrouter import LLMResponse
from app.models.enums import AIFeature, ModuleName, SessionStatus
from app.schemas.ai import ChatRequest


@pytest.mark.asyncio
async def test_workflow_engine_full_pipeline() -> None:
    user_id = uuid4()
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id

    session_repo = MagicMock()
    session_repo.create_session.return_value = session
    session_repo.update_session.return_value = session

    llm_client = MagicMock()
    llm_client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content=(
                '{"teacher":{"thinking_process":"think","concepts":["arrays"],"approach":"two pointers"},'
                '"coder":{"brute_force":{"language":"python","code":"def bf(): pass","complexity":"O(n^2)"},'
                '"better_solution":{"language":"python","code":"def better(): pass"},'
                '"optimal_solution":{"language":"python","code":"def opt(): pass","complexity":"O(n)"}},'
                '"evaluator":{"time_complexity":"O(n)","space_complexity":"O(1)",'
                '"optimizations":["use hash map"],"mistakes":["off-by-one"],'
                '"follow_up_questions":["sorted input?"],"edge_cases":["empty array"]}}'
            ),
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=50,
            completion_tokens=100,
            latency_ms=200,
            estimated_cost=0.0005,
            temperature=0.2,
        ),
    )

    prompt_loader = MagicMock()
    prompt_loader.load.return_value = "system"

    usage_client = MagicMock()
    usage_client.record_usage = AsyncMock()

    from app.services.usage.usage_tracker import UsageTracker

    nodes = WorkflowNodes(
        teacher=TeacherModule(),
        coder=CoderModule(),
        evaluator=EvaluatorModule(),
        llm_client=llm_client,
        prompt_loader=prompt_loader,
        session_repo=session_repo,
        message_repo=MagicMock(),
        execution_trace=MagicMock(record=MagicMock()),
        memory_service=MagicMock(
            build_prompt_context=MagicMock(return_value={}),
            append_response=MagicMock(),
        ),
        usage_tracker=UsageTracker(usage_client=usage_client, model_usage_repo=MagicMock()),
    )
    engine = AIWorkflowEngine(nodes=nodes)

    response = await engine.execute(
        user_id=user_id,
        request=ChatRequest(feature=AIFeature.LEETCODE, message="Solve two sum"),
    )

    assert response.session_id == session_id
    assert response.status == SessionStatus.COMPLETED
    assert len(response.modules) == 4
    assert response.modules[0].module == ModuleName.TEACHER
    assert response.modules[1].module == ModuleName.CODER
    assert "```python" in response.modules[1].content
    assert response.modules[2].module == ModuleName.CODE_EXPLAINER
    assert "Common Mistakes" in response.modules[3].content
    llm_client.chat_completion.assert_awaited()


@pytest.mark.asyncio
async def test_workflow_openrouter_json_failure_partial() -> None:
    user_id = uuid4()
    session = MagicMock()
    session.id = uuid4()
    session_repo = MagicMock()
    session_repo.create_session.return_value = session

    llm_client = MagicMock()
    llm_client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content="invalid json",
            model="m",
            provider="p",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
            estimated_cost=0.0,
        ),
    )

    nodes = WorkflowNodes(
        llm_client=llm_client,
        prompt_loader=MagicMock(load=MagicMock(return_value="sys")),
        session_repo=session_repo,
        message_repo=MagicMock(),
    )
    engine = AIWorkflowEngine(nodes=nodes)
    response = await engine.execute(
        user_id=user_id,
        request=ChatRequest(feature=AIFeature.DSA, message="Explain BFS"),
    )
    assert response.session_id is not None
    assert len(response.modules) == 2
    assert response.modules[0].module == ModuleName.TEACHER
