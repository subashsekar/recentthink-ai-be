"""Workflow streaming tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.teacher.module import TeacherModule
from app.agents.shared.workflow.graph import AIWorkflowEngine
from app.agents.shared.workflow.nodes import WorkflowNodes
from app.clients.openrouter import LLMResponse
from app.models.enums import AIFeature
from app.schemas.ai import ChatRequest


@pytest.mark.asyncio
async def test_execute_stream_emits_token_and_complete() -> None:
    user_id = uuid4()
    session = MagicMock()
    session.id = uuid4()

    session_repo = MagicMock()
    session_repo.create_session.return_value = session
    session_repo.update_session.return_value = session

    llm_payload = (
        '{"teacher":{"thinking_process":"think","concepts":["arrays"],"approach":"two pointers"},'
        '"coder":{"brute_force":{"language":"python","code":"def bf(): pass","complexity":"O(n^2)"},'
        '"better_solution":{"language":"python","code":"def better(): pass"},'
        '"optimal_solution":{"language":"python","code":"def opt(): pass","complexity":"O(n)"}},'
        '"evaluator":{"time_complexity":"O(n)","space_complexity":"O(1)",'
        '"optimizations":["use hash map"],"mistakes":["off-by-one"],'
        '"follow_up_questions":["sorted input?"],"edge_cases":["empty array"]}}'
    )

    async def fake_stream(**_kwargs):
        chunk = json.dumps({"choices": [{"delta": {"content": llm_payload}}]})
        yield chunk

    llm_client = MagicMock()
    llm_client.stream_completion = fake_stream
    llm_client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content=llm_payload,
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=100,
            estimated_cost=0.001,
            temperature=0.2,
        ),
    )
    llm_client.estimate_cost.return_value = 0.001
    llm_client.is_configured = True

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
        cache_manager=MagicMock(get=MagicMock(return_value=None), set=MagicMock(), build_key=MagicMock(return_value=None)),
    )
    engine = AIWorkflowEngine(nodes=nodes)

    events = []
    async for event in engine.execute_stream(
        user_id=user_id,
        request=ChatRequest(feature=AIFeature.LEETCODE, message="Solve two sum"),
    ):
        events.append(event)

    types = [event["type"] for event in events]
    assert "status" in types
    assert "token" in types
    assert "complete" in types
    assert "done" in types
    complete = next(event for event in events if event["type"] == "complete")
    assert complete["response"]["session_id"]
