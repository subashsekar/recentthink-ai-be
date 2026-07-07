"""Platform orchestrator unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.clients.openrouter import LLMResponse
from app.models.enums import AIFeature, SessionStatus
from app.schemas.ai import ChatRequest


@pytest.mark.asyncio
async def test_execute_single_llm_pipeline() -> None:
    user_id = uuid4()
    session_id = uuid4()

    session = MagicMock()
    session.id = session_id

    session_repo = MagicMock()
    session_repo.create_session.return_value = session
    session_repo.update_session.return_value = session

    message_repo = MagicMock()
    execution_repo = MagicMock()
    memory_repo = MagicMock()
    memory_repo.get_by_session_id.return_value = None
    model_usage_repo = MagicMock()

    llm_client = MagicMock()
    llm_client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content=(
                '{"teacher":{"explanation":"Hi","concepts":[],"hints":[]},'
                '"coder":{"language":"python","solutions":[]},'
                '"evaluator":{"time_complexity":"O(n)","space_complexity":"O(1)",'
                '"optimizations":[],"feedback":"ok","interview_questions":[],"analytics":{}}}'
            ),
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=10,
            completion_tokens=20,
            latency_ms=100,
            estimated_cost=0.0001,
        ),
    )

    usage_client = MagicMock()
    usage_client.record_usage = AsyncMock()

    from app.repositories.agent_execution_repository import AgentExecutionRepository
    from app.services.execution_trace import ExecutionTraceService
    from app.services.memory.conversation_memory import ConversationMemoryService
    from app.services.prompt_loader import PromptLoader
    from app.services.usage.usage_tracker import UsageTracker

    prompts_root = MagicMock()
    prompt_loader = PromptLoader(prompts_root=MagicMock())
    prompt_loader.load = MagicMock(return_value="system prompt")

    orchestrator = AIPlatformOrchestrator(
        llm_client=llm_client,
        prompt_loader=prompt_loader,
        session_repo=session_repo,
        message_repo=message_repo,
        execution_trace=ExecutionTraceService(MagicMock()),
        memory_service=ConversationMemoryService(memory_repo),
        usage_tracker=UsageTracker(
            usage_client=usage_client,
            model_usage_repo=model_usage_repo,
        ),
    )

    request = ChatRequest(feature=AIFeature.LEETCODE, message="Explain two sum")
    response = await orchestrator.execute(user_id=user_id, request=request)

    assert response.session_id == session_id
    assert response.status == SessionStatus.COMPLETED
    assert len(response.modules) == 3
    llm_client.chat_completion.assert_awaited_once()
    usage_client.record_usage.assert_awaited_once()
