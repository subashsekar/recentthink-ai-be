"""Chat conversational API tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, FollowUpResponse, ModuleResponse, PlannerOutput
from app.services.chat.chat_service import ChatService
from app.services.chat.export_service import ConversationExportService
from app.services.chat.schemas import (
    ChatContinueRequest,
    ChatExportRequest,
    ChatFeatureSlug,
    ChatFollowUpRequest,
    ChatRegenerateRequest,
    ChatRetryRequest,
    ChatStreamRequest,
    ExportFormat,
    ExportType,
    SessionArchiveRequest,
    SessionPinRequest,
    SessionRenameRequest,
)
from app.services.chat.sse_events import ChatStreamStatus, status_event, token_event
from app.services.history.history_manager import HistoryManager
from app.utils.openrouter_stream import parse_stream_delta
from shared.exceptions.repository import RecordNotFoundError


@pytest.fixture
def user():
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


def _session(owner_id, feature=AIFeature.LEETCODE):
    session = MagicMock()
    session.id = uuid4()
    session.user_id = owner_id
    session.feature = feature
    session.title = "Session"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.model_id = "openai/gpt-4o-mini"
    session.mode_id = None
    session.context_metadata = {"title": "Two Sum"}
    session.is_archived = False
    session.is_pinned = False
    session.last_active_at = None
    session.created_at = datetime.now(UTC)
    session.updated_at = datetime.now(UTC)
    return session


def _planner() -> PlannerOutput:
    return PlannerOutput(
        feature=AIFeature.LEETCODE,
        modules=[ModuleName.TEACHER, ModuleName.CODER, ModuleName.EVALUATOR],
        execution_mode="single_llm",
        metadata={},
    )


def _chat_response(session_id) -> ChatResponse:
    return ChatResponse(
        session_id=session_id,
        status=SessionStatus.COMPLETED,
        planner=_planner(),
        modules=[
            ModuleResponse(
                module=ModuleName.TEACHER,
                content="Teacher output",
                structured={"teacher": {"explanation": "done"}},
            ),
        ],
        model="openai/gpt-4o-mini",
        provider="openai",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=100,
        execution_time_ms=150,
    )


def _build_chat_service(*, user, session, messages=None):
    platform = MagicMock()
    platform.model_registry.resolve_model_id.return_value = session.model_id
    platform.chat = AsyncMock(return_value=_chat_response(session.id))
    platform.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=session.id,
            intent="explain_again",
            teacher=ModuleResponse(module=ModuleName.TEACHER, content="Follow-up"),
            model="openai/gpt-4o-mini",
            input_tokens=5,
            output_tokens=10,
            total_tokens=15,
            latency_ms=50,
            execution_time_ms=60,
        ),
    )
    platform.memory_service = MagicMock()
    platform.memory_service.build_prompt_context.return_value = {"teacher_output": {"explanation": "prior"}}

    orchestrator = MagicMock()

    async def stream_events(*, user_id, request, cancel_check=None, **_kwargs):
        yield {"type": "status", "status": "thinking"}
        yield {"type": "token", "delta": "Hel"}
        yield {"type": "token", "delta": "lo"}
        yield {
            "type": "complete",
            "response": _chat_response(session.id).model_dump(mode="json"),
            "stream_meta": {
                "action": "stream",
                "status": "completed",
                "finish_reason": "stop",
                "missing_sections": None,
                "requested_sections": None,
                "cache_hit": False,
                "retry_count": 0,
                "generation_type": "stream",
            },
        }
        yield {"type": "done"}

    orchestrator.execute_stream = stream_events

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session
    session_repo.touch_last_active = MagicMock()

    message_repo = MagicMock()
    message_repo.list_by_session.return_value = messages or []
    message_repo.list_all_by_session.return_value = messages or []
    message_repo.count_by_session.return_value = len(messages or [])
    message_repo.get_by_id.return_value = None
    message_repo.get_preceding_user_message.return_value = None
    message_repo.update_message.return_value = MagicMock()

    history = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    export = ConversationExportService(
        history_manager=history,
        session_repo=session_repo,
        message_repo=message_repo,
    )

    service = ChatService(
        platform_service=platform,
        orchestrator=orchestrator,
        history_manager=history,
        export_service=export,
        session_repo=session_repo,
        message_repo=message_repo,
    )
    return service, platform, session_repo, message_repo


def test_parse_stream_delta_extracts_text() -> None:
    chunk = json.dumps({"choices": [{"delta": {"content": "hello"}}]})
    assert parse_stream_delta(chunk) == "hello"


def test_sse_helpers_format_events() -> None:
    assert '"type": "status"' in status_event(ChatStreamStatus.THINKING)
    assert '"delta": "x"' in token_event("x")


@pytest.mark.asyncio
async def test_stream_emits_status_token_complete(user) -> None:
    session = _session(user.user_id)
    service, _, history_repo, _ = _build_chat_service(user=user, session=session)

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="Solve two sum", session_id=session.id),
    ):
        frames.append(frame)

    assert any('"status": "thinking"' in frame for frame in frames)
    assert any('"delta": "Hel"' in frame for frame in frames)
    assert any('"type": "complete"' in frame for frame in frames)
    assert any('"type": "done"' in frame for frame in frames)
    history_repo.touch_last_active.assert_called()


@pytest.mark.asyncio
async def test_follow_up_stream(user) -> None:
    session = _session(user.user_id)
    service, platform, _, _ = _build_chat_service(user=user, session=session)
    frames = []
    async for frame in service.follow_up_stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatFollowUpRequest(session_id=session.id, question="Explain again"),
    ):
        frames.append(frame)
    assert any('"type": "complete"' in frame for frame in frames)
    platform.follow_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_reuses_session_and_user_message(user) -> None:
    session = _session(user.user_id)
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.session_id = session.id
    assistant.created_at = datetime.now(UTC)
    assistant.role = MessageRole.ASSISTANT
    assistant.content_metadata = {}

    user_message = MagicMock()
    user_message.content = "Solve two sum"

    service, platform, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.get_by_id.return_value = assistant
    message_repo.get_preceding_user_message.return_value = user_message
    message_repo.list_by_session.return_value = [
        MagicMock(role=MessageRole.USER, content="Solve two sum", content_metadata={}, id=uuid4()),
        MagicMock(
            role=MessageRole.ASSISTANT,
            content="partial",
            content_metadata={},
            id=uuid4(),
        ),
    ]

    result = await service.retry_response(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatRetryRequest(session_id=session.id, message_id=assistant.id),
    )
    assert result.action == "retry"
    assert result.session_id == session.id
    platform.chat.assert_awaited_once()
    assert platform.chat.await_args.args[1].message == "Solve two sum"
    message_repo.update_message.assert_called()


@pytest.mark.asyncio
async def test_regenerate_supersedes_prior_message(user) -> None:
    session = _session(user.user_id)
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.session_id = session.id
    assistant.created_at = datetime.now(UTC)
    assistant.role = MessageRole.ASSISTANT
    assistant.content_metadata = {"structured": {"teacher": {"explanation": "old"}}}
    assistant.module_name = ModuleName.TEACHER
    assistant.content = "old"

    service, platform, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.get_by_id.return_value = assistant
    message_repo.get_preceding_user_message.return_value = MagicMock(content="Solve two sum")
    message_repo.list_by_session.return_value = [assistant]

    result = await service.regenerate_response(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatRegenerateRequest(session_id=session.id, message_id=assistant.id),
    )
    assert result.action == "regenerate"
    metadata_call = message_repo.update_message.call_args_list[0]
    assert metadata_call.args[0] == assistant.id
    assert metadata_call.kwargs["content_metadata"]["status"] == "superseded"
    platform.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_continue_requires_truncated_message(user) -> None:
    session = _session(user.user_id)
    service, _, _, _ = _build_chat_service(user=user, session=session)
    with pytest.raises(RecordNotFoundError):
        await service.continue_response(
            user,
            ChatFeatureSlug.LEETCODE,
            ChatContinueRequest(session_id=session.id),
        )


def test_session_rename_archive_pin(user) -> None:
    session = _session(user.user_id)
    service, _, session_repo, _ = _build_chat_service(user=user, session=session)
    session_repo.update_session.return_value = session

    renamed = service.rename_session(
        user,
        ChatFeatureSlug.LEETCODE,
        session.id,
        SessionRenameRequest(title="New title"),
    )
    assert renamed.title == "Session"
    session_repo.update_session.assert_called()

    session_repo.update_session.reset_mock()
    service.archive_session(
        user,
        ChatFeatureSlug.LEETCODE,
        session.id,
        SessionArchiveRequest(archived=True),
    )
    session_repo.update_session.assert_called_with(session.id, is_archived=True)

    session_repo.update_session.reset_mock()
    service.pin_session(
        user,
        ChatFeatureSlug.LEETCODE,
        session.id,
        SessionPinRequest(pinned=True),
    )
    session_repo.update_session.assert_called_with(session.id, is_pinned=True)


def test_export_conversation_markdown(user) -> None:
    session = _session(user.user_id)
    service, _, session_repo, message_repo = _build_chat_service(user=user, session=session)
    message = MagicMock()
    message.id = uuid4()
    message.role = MessageRole.USER
    message.content = "Hello"
    message.content_metadata = {}
    message.created_at = datetime.now(UTC)
    message.module_name = None

    session_repo.get_by_id.return_value = session
    message_repo.list_all_by_session.return_value = [message]

    exported = service.export_session(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatExportRequest(session_id=session.id, format=ExportFormat.MARKDOWN),
    )
    assert exported.format == ExportFormat.MARKDOWN
    assert "Hello" in exported.content
    assert exported.filename.endswith(".md")


def test_export_conversation_json(user) -> None:
    session = _session(user.user_id)
    service, _, session_repo, message_repo = _build_chat_service(user=user, session=session)
    message_repo.list_all_by_session.return_value = []
    session_repo.get_by_id.return_value = session

    exported = service.export_session(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatExportRequest(
            session_id=session.id,
            format=ExportFormat.JSON,
            export_type=ExportType.CONVERSATION,
        ),
    )
    payload = json.loads(exported.content)
    assert "messages" in payload


@pytest.mark.asyncio
async def test_continue_with_truncated_message(user) -> None:
    session = _session(user.user_id)
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.session_id = session.id
    assistant.created_at = datetime.now(UTC)
    assistant.role = MessageRole.ASSISTANT
    assistant.content_metadata = {
        "status": "truncated",
        "finish_reason": "length",
        "missing_sections": ["coder", "evaluator"],
        "structured": {"teacher": {"explanation": "partial"}},
    }
    assistant.module_name = ModuleName.TEACHER
    assistant.content = "partial"

    service, platform, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.list_by_session.return_value = [assistant]

    result = await service.continue_response(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatContinueRequest(session_id=session.id),
    )
    assert result.action == "continue"
    platform.chat.assert_awaited_once()


def test_feature_slug_mapping() -> None:
    from fastapi import HTTPException

    assert ChatService.resolve_feature(ChatFeatureSlug.LEETCODE) == AIFeature.LEETCODE
    assert ChatService.resolve_feature(ChatFeatureSlug.HACKERRANK) == AIFeature.HACKERRANK
    assert ChatService.resolve_feature(ChatFeatureSlug.DSA_PATTERN) == AIFeature.DSA_PATTERN
    assert ChatService.resolve_feature(ChatFeatureSlug.COURSE_GENERATOR) == AIFeature.COURSE_GENERATOR
    with pytest.raises(HTTPException) as exc_info:
        ChatService.resolve_feature(ChatFeatureSlug.INTERVIEW)
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_stream_persists_assistant_metadata(user) -> None:
    session = _session(user.user_id)
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.role = MessageRole.ASSISTANT
    assistant.content_metadata = {}

    service, _, _, message_repo = _build_chat_service(
        user=user,
        session=session,
        messages=[assistant],
    )

    async for _frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="Solve two sum", session_id=session.id),
    ):
        pass

    metadata_call = message_repo.update_message.call_args
    assert metadata_call is not None
    metadata = metadata_call.kwargs["content_metadata"]
    assert metadata["action"] == "stream"
    assert metadata["model"] == "openai/gpt-4o-mini"
    assert metadata["provider"] == "openai"
    assert metadata["prompt_tokens"] == 10
    assert metadata["completion_tokens"] == 20
    assert metadata["execution_time_ms"] == 150


def test_get_session_include_hidden(user) -> None:
    session = _session(user.user_id)
    service, _, session_repo, message_repo = _build_chat_service(user=user, session=session)
    session_repo.get_by_id.return_value = session
    message_repo.list_by_session.return_value = []
    message_repo.count_by_session.return_value = 0

    service.get_session(
        user,
        ChatFeatureSlug.LEETCODE,
        session.id,
        include_hidden=True,
    )
    session_repo.get_by_id.assert_called()


def test_delete_message_soft_deletes(user) -> None:
    session = _session(user.user_id)
    message = MagicMock()
    message.id = uuid4()
    message.session_id = session.id
    message.content_metadata = {}

    service, _, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.get_by_id.return_value = message

    service.delete_message(user, ChatFeatureSlug.LEETCODE, message.id)
    metadata = message_repo.update_message.call_args.kwargs["content_metadata"]
    assert metadata["deleted"] is True


@pytest.mark.asyncio
async def test_stream_routes_short_follow_up_question(user) -> None:
    session = _session(user.user_id)
    service, platform, _, _ = _build_chat_service(user=user, session=session)

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(session_id=session.id, message="Can you explain again?"),
    ):
        frames.append(frame)

    assert any('"action": "follow_up"' in frame or '"intent"' in frame for frame in frames)
    platform.follow_up.assert_awaited_once()


@pytest.mark.asyncio
async def test_follow_up_stream_cancel_before_call(user) -> None:
    session = _session(user.user_id)
    service, platform, _, _ = _build_chat_service(user=user, session=session)

    async def cancelled():
        return True

    frames = []
    async for frame in service.follow_up_stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatFollowUpRequest(session_id=session.id, question="Explain again"),
        cancel_check=cancelled,
    ):
        frames.append(frame)

    assert any('"type": "error"' in frame for frame in frames)
    assert any('"type": "done"' in frame for frame in frames)
    platform.follow_up.assert_not_awaited()


def test_bookmark_message(user) -> None:
    session = _session(user.user_id)
    message = MagicMock()
    message.id = uuid4()
    message.session_id = session.id
    message.content_metadata = {}
    updated = MagicMock()

    service, _, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.get_by_id.return_value = message
    message_repo.update_message.return_value = updated

    result = service.bookmark_message(
        user,
        ChatFeatureSlug.LEETCODE,
        message.id,
        bookmarked=True,
    )
    assert result is updated
    metadata = message_repo.update_message.call_args.kwargs["content_metadata"]
    assert metadata["bookmarked"] is True


def test_delete_session(user) -> None:
    session = _session(user.user_id)
    service, _, _, _ = _build_chat_service(user=user, session=session)
    history = MagicMock()
    service._history = history
    service.delete_session(user, ChatFeatureSlug.LEETCODE, session.id)
    history.delete_session.assert_called_once()


def test_get_session_wrong_feature_raises(user) -> None:
    session = _session(user.user_id, feature=AIFeature.HACKERRANK)
    service, _, session_repo, _ = _build_chat_service(user=user, session=session)
    session_repo.get_by_id.return_value = session

    with pytest.raises(RecordNotFoundError):
        service.get_session(user, ChatFeatureSlug.LEETCODE, session.id)


@pytest.mark.asyncio
async def test_stream_unhandled_exception_yields_error_done(user) -> None:
    session = _session(user.user_id)
    service, _, session_repo, _ = _build_chat_service(user=user, session=session)

    async def stream_events(**_kwargs):
        raise RuntimeError("boom")
        yield  # pragma: no cover

    service._orchestrator.execute_stream = stream_events

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="Solve two sum", session_id=session.id),
    ):
        frames.append(frame)

    assert any("boom" in frame for frame in frames)
    assert '"type": "done"' in frames[-1]


@pytest.mark.asyncio
async def test_continue_merges_and_deletes_duplicate_assistant(user) -> None:
    session = _session(user.user_id)
    truncated = MagicMock()
    truncated.id = uuid4()
    truncated.session_id = session.id
    truncated.created_at = datetime.now(UTC)
    truncated.role = MessageRole.ASSISTANT
    truncated.content = "partial"
    truncated.content_metadata = {
        "status": "truncated",
        "finish_reason": "length",
        "missing_sections": ["coder"],
        "structured": {"teacher": {"explanation": "partial"}},
    }
    truncated.module_name = ModuleName.TEACHER

    duplicate = MagicMock()
    duplicate.id = uuid4()
    duplicate.session_id = session.id
    duplicate.role = MessageRole.ASSISTANT
    duplicate.content = "new partial"
    duplicate.content_metadata = {
        "structured": {"coder": {"optimal_solution": {"code": "def solve(): pass"}}},
    }

    service, platform, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.list_by_session.return_value = [truncated, duplicate]

    result = await service.continue_response(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatContinueRequest(session_id=session.id),
    )
    assert result.action == "continue"
    platform.chat.assert_awaited_once()
    message_repo.delete_message.assert_called_once_with(duplicate.id)




@pytest.mark.asyncio
async def test_reconnect_stream_replays_completed_assistant(user) -> None:
    session = _session(user.user_id)
    assistant = MagicMock()
    assistant.id = uuid4()
    assistant.session_id = session.id
    assistant.role = MessageRole.ASSISTANT
    assistant.content = "Final answer"
    assistant.content_metadata = {
        "status": "completed",
        "structured": {"teacher": {"explanation": "done"}},
    }
    assistant.created_at = datetime.now(UTC)

    service, _, _, message_repo = _build_chat_service(
        user=user,
        session=session,
        messages=[assistant],
    )

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="ignored on reconnect", session_id=session.id),
        last_event_id="5",
    ):
        frames.append(frame)

    joined = "\n".join(frames)
    assert '"status": "reconnect"' in joined
    assert '"type": "complete"' in joined
    assert '"type": "done"' in joined
    assert str(assistant.id) in joined


@pytest.mark.asyncio
async def test_reconnect_stream_incomplete_prompts_retry(user) -> None:
    session = _session(user.user_id)
    service, _, _, message_repo = _build_chat_service(user=user, session=session)
    message_repo.list_all_by_session.return_value = []

    frames = []
    async for frame in service.stream(
        user,
        ChatFeatureSlug.LEETCODE,
        ChatStreamRequest(message="retry me", session_id=session.id),
        last_event_id="2",
    ):
        frames.append(frame)

    joined = "\n".join(frames)
    assert '"status": "reconnect"' in joined
    assert "incomplete; retry stream" in joined
    assert '"type": "done"' in joined


def test_interview_chat_feature_is_gated(user) -> None:
    from fastapi import HTTPException

    session = _session(user.user_id)
    service, _, _, _ = _build_chat_service(user=user, session=session)

    with pytest.raises(HTTPException) as exc_info:
        service.resolve_feature(ChatFeatureSlug.INTERVIEW)
    assert exc_info.value.status_code == 501
    assert "Interview Trainer" in str(exc_info.value.detail)
