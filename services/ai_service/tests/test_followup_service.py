"""Follow-up service unit tests."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.clients.openrouter import LLMResponse
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, MessageRole, ModuleName
from app.schemas.ai import FollowUpRequest, ModuleResponse
from app.services.followup.followup_service import FollowUpService


def _build_service(*, feature: AIFeature = AIFeature.LEETCODE, context: dict | None = None) -> FollowUpService:
    session_repo = MagicMock()
    message_repo = MagicMock()
    memory_service = MagicMock()
    llm_client = AsyncMock()
    prompt_loader = MagicMock()
    prompt_loader.load.return_value = "system prompt"

    session = MagicMock()
    session.user_id = uuid4()
    session.feature = feature
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = "learning"
    session.context_metadata = context or {
        "title": "Two Sum",
        "description": "Find two numbers that add up to target using a hash map.",
        "difficulty": "Easy",
        "topics": ["Array", "Hash Map"],
    }
    session_repo.get_by_id.return_value = session

    memory_service.build_prompt_context.return_value = {
        "summary": "Discussed two sum",
        "teacher_output": {"approach": "hash map", "concepts": ["Hash Map"]},
        "recent_messages": [{"role": "user", "content": "Analyze Two Sum"}],
        "context": {"problem": session.context_metadata, "feature": feature.value},
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
            "explanation": "HashMap works because lookups are average O(1).",
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

    assistant_msg = MagicMock()
    assistant_msg.id = uuid4()
    assistant_msg.role = MessageRole.ASSISTANT
    assistant_msg.module_name = ModuleName.TEACHER
    assistant_msg.content = "teacher content"
    assistant_msg.content_metadata = {"structured": {"approach": "hash map"}}
    message_repo.list_by_session.return_value = [assistant_msg]

    return FollowUpService(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_service=memory_service,
        llm_client=llm_client,
        prompt_loader=prompt_loader,
    )


@pytest.fixture
def followup_service() -> FollowUpService:
    return _build_service()


@pytest.mark.asyncio
async def test_handle_follow_up_returns_teacher_response(followup_service: FollowUpService) -> None:
    user = AuthenticatedUser(
        user_id=followup_service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    session_id = uuid4()

    result = await followup_service.handle_follow_up(
        user,
        FollowUpRequest(session_id=session_id, question="Explain again please"),
    )
    assert result.intent == "explain_again"
    assert result.context_match is True
    assert result.rejected is False
    assert result.teacher.module.value == "teacher"
    assert "Hash Map" in result.teacher.content or "hash" in result.teacher.content.lower()
    followup_service._memory.append_response.assert_called_once()
    followup_service._llm.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_out_of_context_rejects_without_openrouter() -> None:
    service = _build_service()
    user = AuthenticatedUser(
        user_id=service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    result = await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Who won the FIFA World Cup?"),
    )
    assert result.rejected is True
    assert result.context_match is False
    assert result.intent == "out_of_context"
    assert "LeetCode" in result.teacher.content
    assert result.input_tokens == 0
    service._llm.chat_completion.assert_not_awaited()
    service._memory.append_response.assert_called_once()


@pytest.mark.asyncio
async def test_dsa_pattern_accepts_practice_follow_up() -> None:
    service = _build_service(
        feature=AIFeature.DSA_PATTERN,
        context={"pattern": "Sliding Window", "level": "Beginner", "language": "Python"},
    )
    user = AuthenticatedUser(
        user_id=service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    result = await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Give me another practice problem."),
    )
    assert result.rejected is False
    assert result.context_match is True
    service._llm.chat_completion.assert_awaited_once()


@pytest.mark.asyncio
async def test_course_rejects_unrelated_aws_pricing() -> None:
    service = _build_service(
        feature=AIFeature.COURSE_GENERATOR,
        context={"skill": "Python Basics", "goal": "Learn loops and functions"},
    )
    user = AuthenticatedUser(
        user_id=service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    result = await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Explain AWS pricing."),
    )
    assert result.rejected is True
    assert result.context_match is False
    service._llm.chat_completion.assert_not_awaited()


@pytest.mark.asyncio
async def test_session_not_found_raises() -> None:
    service = _build_service()
    service._sessions.get_by_id.return_value = None
    user = AuthenticatedUser(user_id=uuid4(), email="u@test.com", role="USER")
    with pytest.raises(Exception):
        await service.handle_follow_up(
            user,
            FollowUpRequest(session_id=uuid4(), question="Explain again"),
        )


@pytest.mark.asyncio
async def test_follow_up_persists_user_metadata(followup_service: FollowUpService) -> None:
    user = AuthenticatedUser(
        user_id=followup_service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    await followup_service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Explain complexity"),
    )
    create_calls = followup_service._messages.create_message.call_args_list
    assert create_calls
    user_meta = create_calls[0].kwargs["content_metadata"]
    assert user_meta["message_type"] == "follow_up"
    assert user_meta["context_match"] is True
    assert "prompt_version" in user_meta


@pytest.mark.asyncio
async def test_forbidden_for_other_user() -> None:
    from shared.exceptions.auth import ForbiddenError

    service = _build_service()
    other = AuthenticatedUser(user_id=uuid4(), email="other@test.com", role="USER")
    with pytest.raises(ForbiddenError):
        await service.handle_follow_up(
            other,
            FollowUpRequest(session_id=uuid4(), question="Explain again"),
        )


@pytest.mark.asyncio
async def test_empty_teacher_triggers_retry() -> None:
    service = _build_service()
    short = ModuleResponse(module=ModuleName.TEACHER, content="short")
    good = ModuleResponse(
        module=ModuleName.TEACHER,
        content="A sufficiently long teacher explanation for the follow-up answer.",
        structured={"explanation": "ok"},
    )
    service._teacher = MagicMock()
    # preview (attempt 1), preview (attempt 2), then final persist call
    service._teacher.process.side_effect = [short, short, good]
    user = AuthenticatedUser(
        user_id=service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    result = await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Explain again"),
    )
    assert result.rejected is False
    assert service._llm.chat_completion.await_count == 2
    assert result.teacher.content.startswith("A sufficiently long")


@pytest.mark.asyncio
async def test_usage_tracker_called_on_accept() -> None:
    service = _build_service()
    usage = AsyncMock()
    service._usage = usage
    user = AuthenticatedUser(
        user_id=service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    await service.handle_follow_up(
        user,
        FollowUpRequest(session_id=uuid4(), question="Explain complexity"),
    )
    usage.record_request.assert_awaited_once()


def test_load_session_outputs_extracts_nested_payloads() -> None:
    service = _build_service()
    teacher = MagicMock()
    teacher.role = MessageRole.ASSISTANT
    teacher.module_name = ModuleName.TEACHER
    teacher.content = "teacher text"
    teacher.content_metadata = {
        "structured": {
            "approach": "x",
            "course": {"lessons": [1]},
            "dsa_pattern": {"overview": "y"},
        }
    }
    coder = MagicMock()
    coder.role = MessageRole.ASSISTANT
    coder.module_name = ModuleName.CODER
    coder.content = "coder text only"
    coder.content_metadata = {}
    user_msg = MagicMock()
    user_msg.role = MessageRole.USER
    user_msg.module_name = None
    user_msg.content_metadata = {}
    service._messages.list_by_session.return_value = [user_msg, teacher, coder]
    outputs = service._load_session_outputs(uuid4())
    assert outputs["teacher"]["approach"] == "x"
    assert outputs["course"] == {"lessons": [1]}
    assert outputs["dsa_pattern"] == {"overview": "y"}
    assert outputs["coder"] == "coder text only"


def test_annotate_skips_out_of_context_assistant() -> None:
    service = _build_service()
    msg = MagicMock()
    msg.id = uuid4()
    msg.role = MessageRole.ASSISTANT
    msg.content_metadata = {
        "follow_up_intent": "out_of_context",
        "generation_type": "follow_up",
    }
    service._messages.list_by_session.return_value = [msg]
    service._annotate_assistant_message(
        uuid4(),
        intent="explain_again",
        context_match=True,
        prompt_version="v1",
        generation_type="follow_up",
        rejected=False,
    )
    service._messages.update_message.assert_not_called()
