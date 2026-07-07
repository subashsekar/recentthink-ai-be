"""Follow-up service unit tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.clients.openrouter import LLMResponse
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature
from app.services.followup.followup_service import FollowUpService


@pytest.fixture
def followup_service() -> FollowUpService:
    session_repo = MagicMock()
    message_repo = MagicMock()
    memory_service = MagicMock()
    llm_client = AsyncMock()
    prompt_loader = MagicMock()
    prompt_loader.load.return_value = "system prompt"

    session = MagicMock()
    session.user_id = uuid4()
    session.feature = AIFeature.LEETCODE
    session_repo.get_by_id.return_value = session

    memory_service.build_prompt_context.return_value = {
        "summary": "Discussed two sum",
        "teacher_output": {"approach": "hash map"},
    }

    teacher_json = json.dumps(
        {
            "problem_summary": "Two Sum",
            "thinking_process": "Use complements",
            "concepts": ["Hash Map"],
            "approach": "Store seen values",
            "common_mistakes": ["Nested loops"],
            "analogy": "Finding matching socks",
            "next_step": "Try an example",
        },
    )
    llm_client.chat_completion.return_value = LLMResponse(
        content=teacher_json,
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=100,
        completion_tokens=200,
        latency_ms=400,
        estimated_cost=0.001,
        temperature=0.2,
    )

    return FollowUpService(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_service=memory_service,
        llm_client=llm_client,
        prompt_loader=prompt_loader,
    )


@pytest.mark.asyncio
async def test_handle_follow_up_returns_teacher_response(followup_service: FollowUpService) -> None:
    user = AuthenticatedUser(user_id=followup_service._sessions.get_by_id.return_value.user_id, email="u@test.com", role="USER")
    session_id = uuid4()
    from app.schemas.ai import FollowUpRequest

    result = await followup_service.handle_follow_up(
        user,
        FollowUpRequest(session_id=session_id, question="Explain again please"),
    )
    assert result.intent == "explain_again"
    assert result.teacher.module.value == "teacher"
    assert "Hash Map" in result.teacher.content or "hash" in result.teacher.content.lower()
    followup_service._memory.append_response.assert_called_once()
