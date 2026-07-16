"""Streaming and session-level follow-up behaviour tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.clients.openrouter import LLMResponse
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole, ModuleName
from app.schemas.ai import FollowUpRequest, FollowUpResponse, ModuleResponse
from app.services.chat.chat_service import ChatService
from app.services.chat.schemas import ChatFeatureSlug, ChatFollowUpRequest
from app.services.followup.followup_service import FollowUpService


@pytest.mark.asyncio
async def test_follow_up_stream_includes_rejection_flags() -> None:
    user = AuthenticatedUser(user_id=uuid4(), email="u@test.com", role="USER")
    session = MagicMock()
    session.id = uuid4()
    session.user_id = user.user_id
    session.feature = AIFeature.LEETCODE
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = "learning"

    platform = MagicMock()
    platform.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session.id,
            intent="out_of_context",
            teacher=ModuleResponse(
                module=ModuleName.TEACHER,
                content="This conversation is dedicated to your current LeetCode session.",
            ),
            context_match=False,
            rejected=True,
        )
    )
    sessions = MagicMock()
    sessions.get_by_id.return_value = session
    service = ChatService(
        platform_service=platform,
        history_manager=MagicMock(),
        session_repo=sessions,
        message_repo=MagicMock(),
        orchestrator=MagicMock(),
        export_service=MagicMock(),
    )

    frames: list[str] = []
    async for frame in service.follow_up_stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatFollowUpRequest(session_id=session.id, question="Tell me a joke"),
    ):
        frames.append(frame)

    joined = "\n".join(frames)
    assert '"rejected": true' in joined
    assert '"context_match": false' in joined
    assert "out_of_context" in joined
    assert '"type": "done"' in joined
    platform.follow_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_follow_up_keeps_session_and_history() -> None:
    session_repo = MagicMock()
    message_repo = MagicMock()
    memory_service = MagicMock()
    llm_client = AsyncMock()
    prompt_loader = MagicMock()
    prompt_loader.load.return_value = "system"

    session_id = uuid4()
    user_id = uuid4()
    session = MagicMock()
    session.user_id = user_id
    session.feature = AIFeature.HACKERRANK
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = "learning"
    session.context_metadata = {
        "title": "SQL Aggregation",
        "description": "Write an SQL query to aggregate weather data.",
        "domain": "SQL",
    }
    session_repo.get_by_id.return_value = session
    memory_service.build_prompt_context.return_value = {
        "summary": "Explained SQL aggregation",
        "teacher_output": {"approach": "GROUP BY"},
        "recent_messages": [],
        "context": {"problem": session.context_metadata},
    }
    llm_client.chat_completion.return_value = LLMResponse(
        content=json.dumps(
            {
                "problem_summary": "SQL Aggregation",
                "thinking_process": "Aggregate then filter",
                "concepts": ["GROUP BY"],
                "approach": "Use aggregation",
                "common_mistakes": ["Missing GROUP BY"],
                "analogy": "Sorting mail by city",
                "next_step": "Try HAVING",
                "explanation": "The SQL query groups rows before selecting aggregates.",
            }
        ),
        model="openai/gpt-4o-mini",
        provider="openai",
        prompt_tokens=50,
        completion_tokens=80,
        latency_ms=120,
        estimated_cost=0.0,
        temperature=0.2,
    )
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.role = MessageRole.ASSISTANT
    assistant.module_name = ModuleName.TEACHER
    assistant.content_metadata = {"structured": {}}
    message_repo.list_by_session.return_value = [assistant]

    service = FollowUpService(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_service=memory_service,
        llm_client=llm_client,
        prompt_loader=prompt_loader,
    )
    user = AuthenticatedUser(user_id=user_id, email="u@test.com", role="USER")
    result = await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=session_id, question="Explain the SQL query."),
    )
    assert result.session_id == session_id
    assert result.rejected is False
    # Same session reused — no new session creation.
    assert not hasattr(session_repo, "create") or not session_repo.create.called
    memory_service.append_response.assert_called_once()
    assert message_repo.create_message.call_count >= 1
