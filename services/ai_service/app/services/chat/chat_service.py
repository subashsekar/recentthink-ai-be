"""Conversational chat orchestration service."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.ai_message import AIMessage
from app.models.enums import AIFeature, MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import ChatRequest, ChatResponse, FollowUpRequest, FollowUpResponse
from app.services.ai_platform_service import AIPlatformService
from app.services.chat.message_metadata import (
    build_assistant_metadata,
    is_truncated_finish_reason,
    should_hide_message,
)
from app.services.chat.stream_cancel import StreamCancelledError
from app.services.chat.export_service import ConversationExportService
from app.services.chat.schemas import (
    FEATURE_SLUG_MAP,
    ChatActionResponse,
    ChatContinueRequest,
    ChatExportRequest,
    ChatExportResponse,
    ChatFeatureSlug,
    ChatFollowUpRequest,
    ChatRegenerateRequest,
    ChatRetryRequest,
    ChatStreamRequest,
    SessionArchiveRequest,
    SessionPinRequest,
    SessionRenameRequest,
)
from app.services.chat.sse_events import (
    ChatStreamStatus,
    SseEventCounter,
    complete_event,
    done_event,
    error_event,
    status_event,
    token_event,
)
from app.services.history.history_manager import HistoryManager
from app.utils.section_tokens import merge_llm_payload, resolve_prior_payload
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)


class ChatService:
    """Thin conversational façade over the existing AI platform."""

    def __init__(
        self,
        *,
        platform_service: AIPlatformService,
        orchestrator: AIPlatformOrchestrator,
        history_manager: HistoryManager,
        export_service: ConversationExportService,
        session_repo: AISessionRepository,
        message_repo: AIMessageRepository,
    ) -> None:
        self._platform = platform_service
        self._orchestrator = orchestrator
        self._history = history_manager
        self._export = export_service
        self._sessions = session_repo
        self._messages = message_repo

    @staticmethod
    def resolve_feature(slug: ChatFeatureSlug) -> AIFeature:
        if slug == ChatFeatureSlug.INTERVIEW:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=(
                    "Interview Trainer is not implemented. "
                    "Out of scope for this portfolio release."
                ),
            )
        return FEATURE_SLUG_MAP[slug]

    def _ensure_session_access(self, user: AuthenticatedUser, session_id: UUID):
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")
        return session

    def _touch_session(self, session_id: UUID) -> None:
        self._history.touch_session(session_id)

    def _build_chat_request(
        self,
        feature: AIFeature,
        payload: ChatStreamRequest,
        *,
        message: str | None = None,
        requested_sections: list[str] | None = None,
        context: dict[str, Any] | None = None,
        action: str = "stream",
    ) -> ChatRequest:
        return ChatRequest(
            feature=feature,
            message=message or payload.message,
            session_id=payload.session_id,
            title=payload.title,
            context=context if context is not None else payload.context,
            model=payload.model,
            mode_id=payload.mode_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            requested_sections=requested_sections or payload.requested_sections,
        )

    async def stream(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatStreamRequest,
        *,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        last_event_id: str | None = None,
    ) -> AsyncIterator[str]:
        feature = self.resolve_feature(feature_slug)
        event_ids = SseEventCounter()

        if last_event_id and payload.session_id is not None:
            async for frame in self._reconnect_stream(user, payload.session_id, event_ids=event_ids):
                yield frame
            return

        if self._should_route_follow_up(payload):
            follow_up = ChatFollowUpRequest(
                session_id=payload.session_id,  # type: ignore[arg-type]
                question=payload.message,
                model=payload.model,
                mode_id=payload.mode_id,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
                requested_sections=payload.requested_sections,
            )
            async for event in self.follow_up_stream(
                user,
                feature_slug,
                follow_up,
                cancel_check=cancel_check,
                event_ids=event_ids,
            ):
                yield event
            return

        request = self._build_chat_request(feature, payload, action="stream")
        if payload.session_id is not None:
            self._ensure_session_access(user, payload.session_id)

        resolved_model = self._platform.model_registry.resolve_model_id(
            requested=request.model,
            session_model_id=(
                self._sessions.get_by_id(payload.session_id).model_id
                if payload.session_id is not None
                else None
            ),
        )
        request = request.model_copy(update={"model": resolved_model})

        try:
            async for event in self._orchestrator.execute_stream(
                user_id=user.user_id,
                request=request,
                cancel_check=cancel_check,
            ):
                event_type = event.get("type")
                eid = event_ids.next()
                if event_type == "status":
                    yield status_event(
                        ChatStreamStatus(str(event.get("status", "thinking"))),
                        event_id=eid,
                    )
                elif event_type == "token":
                    yield token_event(str(event.get("delta", "")), event_id=eid)
                elif event_type == "complete":
                    response = ChatResponse.model_validate(event["response"])
                    stream_meta = event.get("stream_meta") if isinstance(event.get("stream_meta"), dict) else {}
                    self._persist_stream_metadata(
                        response.session_id,
                        response=response,
                        stream_meta=stream_meta,
                        requested_sections=request.requested_sections,
                    )
                    self._touch_session(response.session_id)
                    yield complete_event(event["response"], event_id=eid)
                elif event_type == "error":
                    yield error_event(str(event.get("message", "Stream failed")), event_id=eid)
                elif event_type == "done":
                    yield done_event(event_id=eid)
        except StreamCancelledError:
            yield error_event("Stream cancelled.", event_id=event_ids.next())
            yield done_event(event_id=event_ids.next())
        except Exception as exc:
            logger.exception("chat_stream_failed", extra={"feature": feature.value})
            yield error_event(str(exc), event_id=event_ids.next())
            yield done_event(event_id=event_ids.next())

    async def _reconnect_stream(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        event_ids: SseEventCounter,
    ) -> AsyncIterator[str]:
        """Handle SSE reconnect via Last-Event-ID after a completed turn."""
        self._ensure_session_access(user, session_id)
        latest = self._latest_assistant_message(session_id)
        if latest is None:
            yield status_event(
                ChatStreamStatus.RECONNECT,
                detail="incomplete; retry stream",
                event_id=event_ids.next(),
            )
            yield done_event(event_id=event_ids.next())
            return

        metadata = latest.content_metadata or {}
        status = str(metadata.get("status", "")).lower()
        if status in {"completed", "truncated"} or metadata.get("structured"):
            yield status_event(
                ChatStreamStatus.RECONNECT,
                detail="complete already persisted",
                event_id=event_ids.next(),
            )
            complete_payload: dict[str, Any] = {
                "session_id": str(session_id),
                "message_id": str(latest.id),
                "status": status or "completed",
                "content": latest.content,
            }
            if isinstance(metadata.get("structured"), dict):
                complete_payload["structured"] = metadata["structured"]
            yield complete_event(complete_payload, event_id=event_ids.next())
            yield done_event(event_id=event_ids.next())
            return

        yield status_event(
            ChatStreamStatus.RECONNECT,
            detail="incomplete; retry stream",
            event_id=event_ids.next(),
        )
        yield done_event(event_id=event_ids.next())

    async def follow_up_stream(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatFollowUpRequest,
        *,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        event_ids: SseEventCounter | None = None,
    ) -> AsyncIterator[str]:
        ids = event_ids or SseEventCounter()
        try:
            if cancel_check is not None and await cancel_check():
                yield error_event("Stream cancelled.", event_id=ids.next())
                yield done_event(event_id=ids.next())
                return
            yield status_event(ChatStreamStatus.THINKING, event_id=ids.next())
            yield status_event(ChatStreamStatus.GENERATING, event_id=ids.next())
            response = await self.follow_up(user, feature_slug, payload)
            yield complete_event(
                {
                    "session_id": str(response.session_id),
                    "intent": response.intent,
                    "teacher": response.teacher.model_dump(mode="json"),
                    "model": response.model,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "latency_ms": response.latency_ms,
                    "execution_time_ms": response.execution_time_ms,
                    "context_match": response.context_match,
                    "rejected": response.rejected,
                    "action": "follow_up",
                },
                event_id=ids.next(),
            )
            yield done_event(event_id=ids.next())
        except Exception as exc:
            logger.exception("follow_up_stream_failed")
            yield error_event(str(exc), event_id=ids.next())
            yield done_event(event_id=ids.next())
    @staticmethod
    def _should_route_follow_up(payload: ChatStreamRequest) -> bool:
        if payload.session_id is None:
            return False
        if payload.requested_sections:
            return False
        message = payload.message.strip().lower()
        if len(message) > 240:
            return False
        follow_up_markers = (
            "explain",
            "again",
            "slower",
            "example",
            "another",
            "only",
            "quiz",
            "solution",
            "complexity",
            "easier",
            "continue",
            "clarify",
            "what about",
            "can you",
            "give me",
        )
        return any(marker in message for marker in follow_up_markers)

    async def continue_response(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatContinueRequest,
    ) -> ChatActionResponse:
        feature = self.resolve_feature(feature_slug)
        session = self._ensure_session_access(user, payload.session_id)
        assistant_message = self._resolve_truncated_assistant_message(payload.session_id, payload.message_id)
        metadata = assistant_message.content_metadata or {}
        if not is_truncated_finish_reason(str(metadata.get("finish_reason", ""))) and str(
            metadata.get("status", ""),
        ).lower() != "truncated":
            raise RecordNotFoundError("Target assistant message is not truncated.")

        prior_response = metadata.get("structured") or self._structured_from_message(assistant_message)
        memory_context = (
            self._platform.memory_service.build_prompt_context(payload.session_id)
            if self._platform.memory_service is not None
            else {}
        )
        prior_payload = resolve_prior_payload(
            context={"prior_llm_raw": prior_response} if prior_response else None,
            memory_context=memory_context if isinstance(memory_context, dict) else None,
        )
        missing_sections = metadata.get("missing_sections")
        if not isinstance(missing_sections, list) or not missing_sections:
            raise RecordNotFoundError("No missing sections found in persisted metadata for continue.")
        requested_sections = [str(section) for section in missing_sections]

        stream_payload = ChatStreamRequest(
            message="Continue generating the remaining content without repeating previous sections.",
            session_id=payload.session_id,
            model=payload.model or session.model_id,
            mode_id=payload.mode_id or session.mode_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            requested_sections=requested_sections,
            context={"prior_llm_raw": prior_payload or prior_response},
        )
        request = self._build_chat_request(
            feature,
            stream_payload,
            message=stream_payload.message,
            context=stream_payload.context,
            action="continue",
            requested_sections=requested_sections,
        )
        response = await self._platform.chat(user, request)
        self._finalize_continue_assistant(
            truncated_message=assistant_message,
            response=response,
            requested_sections=requested_sections,
            prior_structured=prior_response,
        )
        self._touch_session(payload.session_id)
        return ChatActionResponse(
            session_id=payload.session_id,
            message_id=assistant_message.id,
            action="continue",
            response=response,
        )

    async def retry_response(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatRetryRequest,
    ) -> ChatActionResponse:
        feature = self.resolve_feature(feature_slug)
        session = self._ensure_session_access(user, payload.session_id)
        assistant_message = self._messages.get_by_id(payload.message_id)
        if assistant_message is None or assistant_message.session_id != payload.session_id:
            raise RecordNotFoundError(f"Message '{payload.message_id}' not found.")
        user_message = self._messages.get_preceding_user_message(
            payload.session_id,
            before_created_at=assistant_message.created_at,
        )
        if user_message is None:
            raise RecordNotFoundError("No preceding user message found for retry.")

        metadata = assistant_message.content_metadata or {}
        metadata["status"] = metadata.get("status") or "failed"
        self._messages.update_message(assistant_message.id, content_metadata=metadata)

        request = ChatRequest(
            feature=feature,
            message=user_message.content,
            session_id=payload.session_id,
            model=payload.model or session.model_id,
            mode_id=payload.mode_id or session.mode_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            context=session.context_metadata,
        )
        response = await self._platform.chat(user, request)
        self._annotate_latest_assistant(
            payload.session_id,
            action="retry",
            prior_message_id=assistant_message.id,
            response=response,
            status="completed",
            generation_type="retry",
        )
        self._touch_session(payload.session_id)
        return ChatActionResponse(
            session_id=payload.session_id,
            message_id=payload.message_id,
            action="retry",
            response=response,
        )

    async def regenerate_response(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatRegenerateRequest,
    ) -> ChatActionResponse:
        feature = self.resolve_feature(feature_slug)
        session = self._ensure_session_access(user, payload.session_id)
        assistant_message = self._messages.get_by_id(payload.message_id)
        if assistant_message is None or assistant_message.session_id != payload.session_id:
            raise RecordNotFoundError(f"Message '{payload.message_id}' not found.")

        metadata = assistant_message.content_metadata or {}
        metadata["status"] = "superseded"
        self._messages.update_message(assistant_message.id, content_metadata=metadata)

        user_message = self._messages.get_preceding_user_message(
            payload.session_id,
            before_created_at=assistant_message.created_at,
        )
        message = user_message.content if user_message else "Regenerate the previous assistant response."
        memory_context = (
            self._platform.memory_service.build_prompt_context(payload.session_id)
            if self._platform.memory_service is not None
            else {}
        )
        prior_response = self._structured_from_message(assistant_message)
        context = dict(session.context_metadata or {})
        if prior_response:
            context["prior_llm_raw"] = prior_response
        if isinstance(memory_context, dict):
            context.setdefault("memory", memory_context)

        request = ChatRequest(
            feature=feature,
            message=message,
            session_id=payload.session_id,
            model=payload.model or session.model_id,
            mode_id=payload.mode_id or session.mode_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            requested_sections=payload.requested_sections,
            context=context or None,
        )
        response = await self._platform.chat(user, request)
        self._annotate_latest_assistant(
            payload.session_id,
            action="regenerate",
            prior_message_id=assistant_message.id,
            response=response,
            status="completed",
            regenerated_from=assistant_message.id,
            generation_type="regenerate",
        )
        self._touch_session(payload.session_id)
        return ChatActionResponse(
            session_id=payload.session_id,
            message_id=payload.message_id,
            action="regenerate",
            response=response,
        )

    async def follow_up(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatFollowUpRequest,
    ) -> FollowUpResponse:
        self._ensure_session_access(user, payload.session_id)
        request = FollowUpRequest(
            session_id=payload.session_id,
            question=payload.question,
            model=payload.model,
            mode_id=payload.mode_id,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            requested_sections=payload.requested_sections,
        )
        response = await self._platform.follow_up(user, request)
        self._touch_session(payload.session_id)
        return response

    def list_sessions(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        *,
        search: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ):
        feature = self.resolve_feature(feature_slug)
        return self._history.list_history(
            user,
            feature=feature,
            search=search,
            include_archived=include_archived,
            limit=limit,
            offset=offset,
        )

    def get_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
        include_hidden: bool = False,
    ):
        session = self._ensure_session_access(user, session_id)
        if session.feature != self.resolve_feature(feature_slug):
            raise RecordNotFoundError(f"Session '{session_id}' not found for feature '{feature_slug.value}'.")
        return self._history.get_session_detail(
            user,
            session_id,
            limit=limit,
            offset=offset,
            include_hidden=include_hidden,
        )

    def rename_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
        payload: SessionRenameRequest,
    ):
        self._ensure_feature_session(user, feature_slug, session_id)
        return self._history.rename_session(user, session_id, title=payload.title)

    def archive_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
        payload: SessionArchiveRequest,
    ):
        self._ensure_feature_session(user, feature_slug, session_id)
        return self._history.archive_session(user, session_id, archived=payload.archived)

    def pin_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
        payload: SessionPinRequest,
    ):
        self._ensure_feature_session(user, feature_slug, session_id)
        return self._history.pin_session(user, session_id, pinned=payload.pinned)

    def delete_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
    ) -> None:
        self._ensure_feature_session(user, feature_slug, session_id)
        self._history.delete_session(user, session_id)

    def export_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        payload: ChatExportRequest,
    ) -> ChatExportResponse:
        self._ensure_feature_session(user, feature_slug, payload.session_id)
        return self._export.export_session(user, payload)

    def bookmark_message(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        message_id: UUID,
        *,
        bookmarked: bool,
    ):
        message = self._messages.get_by_id(message_id)
        if message is None:
            raise RecordNotFoundError(f"Message '{message_id}' not found.")
        self._ensure_feature_session(user, feature_slug, message.session_id)
        metadata = dict(message.content_metadata or {})
        metadata["bookmarked"] = bookmarked
        updated = self._messages.update_message(message_id, content_metadata=metadata)
        return updated

    def delete_message(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        message_id: UUID,
    ) -> None:
        message = self._messages.get_by_id(message_id)
        if message is None:
            raise RecordNotFoundError(f"Message '{message_id}' not found.")
        self._ensure_feature_session(user, feature_slug, message.session_id)
        metadata = dict(message.content_metadata or {})
        metadata["deleted"] = True
        self._messages.update_message(message_id, content_metadata=metadata)

    def _ensure_feature_session(
        self,
        user: AuthenticatedUser,
        feature_slug: ChatFeatureSlug,
        session_id: UUID,
    ):
        session = self._ensure_session_access(user, session_id)
        if session.feature != self.resolve_feature(feature_slug):
            raise RecordNotFoundError(f"Session '{session_id}' not found for feature '{feature_slug.value}'.")
        return session

    def _resolve_truncated_assistant_message(self, session_id: UUID, message_id: UUID | None) -> AIMessage:
        if message_id is not None:
            message = self._messages.get_by_id(message_id)
            if message is None or message.session_id != session_id:
                raise RecordNotFoundError(f"Message '{message_id}' not found.")
            return message
        messages = self._messages.list_by_session(session_id, limit=5000, offset=0)
        for message in reversed(messages):
            if message.role != MessageRole.ASSISTANT:
                continue
            metadata = message.content_metadata or {}
            if should_hide_message(metadata, include_hidden=False):
                continue
            finish_reason = str(metadata.get("finish_reason", "")).lower()
            status = str(metadata.get("status", "")).lower()
            if is_truncated_finish_reason(finish_reason) or status == "truncated":
                return message
        raise RecordNotFoundError("No truncated assistant message found to continue.")

    def _persist_stream_metadata(
        self,
        session_id: UUID,
        *,
        response: ChatResponse,
        stream_meta: dict[str, Any],
        requested_sections: list[str] | None,
    ) -> None:
        metadata = build_assistant_metadata(
            response,
            action=str(stream_meta.get("action", "stream")),
            status=str(stream_meta.get("status", "completed")),
            finish_reason=stream_meta.get("finish_reason"),
            missing_sections=stream_meta.get("missing_sections"),
            requested_sections=requested_sections or stream_meta.get("requested_sections"),
            cache_hit=bool(stream_meta.get("cache_hit", False)),
            retry_count=int(stream_meta.get("retry_count", 0)),
            generation_type=str(stream_meta.get("generation_type", "stream")),
        )
        if stream_meta.get("section_tokens"):
            metadata["section_tokens"] = stream_meta["section_tokens"]
        latest = self._latest_assistant_message(session_id)
        if latest is None:
            return
        existing = dict(latest.content_metadata or {})
        existing.update(metadata)
        self._messages.update_message(latest.id, content_metadata=existing)

    def _annotate_latest_assistant(
        self,
        session_id: UUID,
        *,
        action: str,
        prior_message_id: UUID | None,
        response: ChatResponse,
        status: str,
        regenerated_from: UUID | None = None,
        generation_type: str | None = None,
        finish_reason: str | None = None,
        missing_sections: list[str] | None = None,
        requested_sections: list[str] | None = None,
        cache_hit: bool = False,
        retry_count: int = 0,
    ) -> None:
        latest = self._latest_assistant_message(session_id)
        if latest is None:
            return
        metadata = build_assistant_metadata(
            response,
            action=action,
            status=status,
            finish_reason=finish_reason,
            missing_sections=missing_sections,
            requested_sections=requested_sections,
            cache_hit=cache_hit,
            retry_count=retry_count,
            generation_type=generation_type or action,
            prior_message_id=str(prior_message_id) if prior_message_id else None,
            regenerated_from_message_id=str(regenerated_from) if regenerated_from else None,
        )
        existing = dict(latest.content_metadata or {})
        existing.update(metadata)
        self._messages.update_message(latest.id, content_metadata=existing)

    def _finalize_continue_assistant(
        self,
        *,
        truncated_message: AIMessage,
        response: ChatResponse,
        requested_sections: list[str],
        prior_structured: dict[str, Any] | None,
    ) -> None:
        latest = self._latest_assistant_message(truncated_message.session_id)
        if latest is None:
            return

        latest_meta = latest.content_metadata or {}
        generated = latest_meta.get("structured") if isinstance(latest_meta.get("structured"), dict) else None
        merged_structured = prior_structured
        if isinstance(generated, dict) and prior_structured:
            merged_structured = merge_llm_payload(
                prior_structured,
                generated,
                requested_sections=requested_sections,
            )
        elif isinstance(generated, dict):
            merged_structured = generated

        content = latest.content if latest.id != truncated_message.id else truncated_message.content
        metadata = build_assistant_metadata(
            response,
            action="continue",
            status="completed",
            finish_reason=None,
            missing_sections=None,
            requested_sections=requested_sections,
            prior_message_id=str(truncated_message.id),
            structured=merged_structured if isinstance(merged_structured, dict) else None,
            generation_type="continue",
        )
        existing = dict(truncated_message.content_metadata or {})
        existing.update(metadata)
        self._messages.update_message(
            truncated_message.id,
            content=content,
            content_metadata=existing,
        )
        if latest.id != truncated_message.id:
            self._messages.delete_message(latest.id)

    def _latest_assistant_message(self, session_id: UUID) -> AIMessage | None:
        messages = self._messages.list_by_session(session_id, limit=5000, offset=0)
        assistants = [message for message in messages if message.role == MessageRole.ASSISTANT]
        return assistants[-1] if assistants else None

    @staticmethod
    def _structured_from_message(message: AIMessage) -> dict[str, Any] | None:
        metadata = message.content_metadata or {}
        structured = metadata.get("structured")
        if isinstance(structured, dict):
            return structured
        if message.module_name == ModuleName.TEACHER:
            return {"teacher": {"content": message.content}}
        return None
