"""Streaming cancellation and lifecycle tests."""

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
from app.models.enums import AIFeature, MessageRole
from app.schemas.ai import ChatRequest
from app.services.chat.chat_service import ChatService
from app.services.chat.schemas import ChatFeatureSlug, ChatStreamRequest
from app.services.chat.stream_cancel import StreamCancelledError


@pytest.fixture
def user():
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


def _workflow_nodes(*, stream_impl, message_repo=None):
    session_repo = MagicMock()
    session = MagicMock()
    session.id = uuid4()
    session_repo.create_session.return_value = session
    session_repo.update_session.return_value = session

    llm_client = MagicMock()
    llm_client.stream_completion = stream_impl
    llm_client.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content="{}",
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
            estimated_cost=0.0,
            temperature=0.2,
        ),
    )
    llm_client.estimate_cost.return_value = 0.0
    llm_client.is_configured = True

    repo = message_repo or MagicMock()
    repo.list_by_session.return_value = []

    from app.services.usage.usage_tracker import UsageTracker

    return WorkflowNodes(
        teacher=TeacherModule(),
        coder=CoderModule(),
        evaluator=EvaluatorModule(),
        llm_client=llm_client,
        prompt_loader=MagicMock(load=MagicMock(return_value="system")),
        session_repo=session_repo,
        message_repo=repo,
        execution_trace=MagicMock(record=MagicMock()),
        memory_service=MagicMock(
            build_prompt_context=MagicMock(return_value={}),
            append_response=MagicMock(),
        ),
        usage_tracker=UsageTracker(usage_client=MagicMock(record_usage=AsyncMock()), model_usage_repo=MagicMock()),
        cache_manager=MagicMock(get=MagicMock(return_value=None), set=MagicMock(), build_key=MagicMock(return_value=None)),
    )


@pytest.mark.asyncio
async def test_execute_stream_cancel_during_openrouter_yields_error_done() -> None:
    cancelled = False

    async def fake_stream(**_kwargs):
        nonlocal cancelled
        cancelled = True
        chunk = json.dumps({"choices": [{"delta": {"content": "partial"}}]})
        yield chunk
        raise StreamCancelledError("Client disconnected.")

    nodes = _workflow_nodes(stream_impl=fake_stream)
    engine = AIWorkflowEngine(nodes=nodes)

    events = []
    async for event in engine.execute_stream(
        user_id=uuid4(),
        request=ChatRequest(feature=AIFeature.LEETCODE, message="Solve two sum"),
    ):
        events.append(event)

    assert cancelled
    assert events[-2]["type"] == "error"
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_execute_stream_cancel_check_before_pipeline() -> None:
    call_count = 0

    async def cancel_check():
        nonlocal call_count
        call_count += 1
        return call_count >= 2

    async def fake_stream(**_kwargs):
        chunk = json.dumps({"choices": [{"delta": {"content": "{}"}}]})
        yield chunk

    nodes = _workflow_nodes(stream_impl=fake_stream)
    engine = AIWorkflowEngine(nodes=nodes)

    events = []
    async for event in engine.execute_stream(
        user_id=uuid4(),
        request=ChatRequest(feature=AIFeature.LEETCODE, message="Solve two sum"),
        cancel_check=cancel_check,
    ):
        events.append(event)

    assert any(event["type"] == "error" for event in events)
    assert events[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_chat_service_stream_cancel_error_done(user) -> None:
    from datetime import UTC, datetime

    from app.models.enums import SessionStatus

    session = MagicMock()
    session.id = uuid4()
    session.user_id = user.user_id
    session.feature = AIFeature.LEETCODE
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = None
    session.context_metadata = {}
    session.status = SessionStatus.COMPLETED
    session.title = "Session"
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)

    platform = MagicMock()
    platform.model_registry.resolve_model_id.return_value = session.model_id

    async def stream_events(**_kwargs):
        raise StreamCancelledError("Client disconnected.")
        yield  # pragma: no cover - makes this an async generator

    orchestrator = MagicMock()
    orchestrator.execute_stream = stream_events

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session

    service = ChatService(
        platform_service=platform,
        orchestrator=orchestrator,
        history_manager=MagicMock(),
        export_service=MagicMock(),
        session_repo=session_repo,
        message_repo=MagicMock(),
    )

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="Solve two sum", session_id=session.id),
    ):
        frames.append(frame)

    assert any('"type": "error"' in frame for frame in frames)
    assert any('"type": "done"' in frame for frame in frames)


@pytest.mark.asyncio
async def test_chat_service_stream_error_event_always_done(user) -> None:
    from datetime import UTC, datetime

    from app.models.enums import SessionStatus

    session = MagicMock()
    session.id = uuid4()
    session.user_id = user.user_id
    session.feature = AIFeature.LEETCODE
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = None
    session.context_metadata = {}
    session.status = SessionStatus.COMPLETED
    session.title = "Session"
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)

    platform = MagicMock()
    platform.model_registry.resolve_model_id.return_value = session.model_id

    async def stream_events(**_kwargs):
        yield {"type": "status", "status": "thinking"}
        yield {"type": "error", "message": "Planner failed"}
        yield {"type": "done"}

    orchestrator = MagicMock()
    orchestrator.execute_stream = stream_events

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session

    service = ChatService(
        platform_service=platform,
        orchestrator=orchestrator,
        history_manager=MagicMock(),
        export_service=MagicMock(),
        session_repo=session_repo,
        message_repo=MagicMock(),
    )

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="Solve two sum", session_id=session.id),
    ):
        frames.append(frame)

    assert any('"message": "Planner failed"' in frame for frame in frames)
    assert frames[-1].endswith("\n\n")
    assert '"type": "done"' in frames[-1]
