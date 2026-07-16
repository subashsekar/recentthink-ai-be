"""Conversational chat HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.rate_limit import AI_CHAT_RATE_LIMIT, limiter
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_chat_service
from app.schemas.ai import FollowUpResponse, HistoryListResponse, SessionDetailResponse, SessionSummaryResponse
from app.services.chat.chat_service import ChatService
from app.services.chat.schemas import (
    ChatActionResponse,
    ChatContinueRequest,
    ChatExportRequest,
    ChatExportResponse,
    ChatFeatureSlug,
    ChatFollowUpRequest,
    ChatRegenerateRequest,
    ChatRetryRequest,
    ChatStreamRequest,
    MessageBookmarkRequest,
    SessionArchiveRequest,
    SessionPinRequest,
    SessionRenameRequest,
)

router = APIRouter(prefix="/chat", tags=["chat"])


def require_supported_chat_feature(feature: ChatFeatureSlug) -> ChatFeatureSlug:
    """Reject Interview Trainer chat routes with HTTP 501 (scaffold only)."""
    ChatService.resolve_feature(feature)
    return feature


@router.post("/{feature}/stream")
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat_stream(
    request: Request,
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatStreamRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    last_event_id = request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")

    async def event_generator():
        async for frame in service.stream(
            user,
            feature,
            payload,
            cancel_check=request.is_disconnected,
            last_event_id=last_event_id,
        ):
            yield frame

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{feature}/continue", response_model=ChatActionResponse)
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat_continue(
    request: Request,
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatContinueRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatActionResponse:
    return await service.continue_response(user, feature, payload)


@router.post("/{feature}/retry", response_model=ChatActionResponse)
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat_retry(
    request: Request,
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatRetryRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatActionResponse:
    return await service.retry_response(user, feature, payload)


@router.post("/{feature}/regenerate", response_model=ChatActionResponse)
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat_regenerate(
    request: Request,
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatRegenerateRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatActionResponse:
    return await service.regenerate_response(user, feature, payload)


@router.post("/{feature}/follow-up", response_model=FollowUpResponse)
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat_follow_up(
    request: Request,
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatFollowUpRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> FollowUpResponse:
    return await service.follow_up(user, feature, payload)


@router.get("/{feature}/sessions", response_model=HistoryListResponse)
def list_chat_sessions(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    search: str | None = Query(default=None, max_length=200),
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryListResponse:
    return service.list_sessions(
        user,
        feature,
        search=search,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/{feature}/sessions/{session_id}", response_model=SessionDetailResponse)
def get_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    include_hidden: bool = Query(default=False),
) -> SessionDetailResponse:
    return service.get_session(
        user,
        feature,
        session_id,
        limit=limit,
        offset=offset,
        include_hidden=include_hidden,
    )


@router.patch("/{feature}/sessions/{session_id}/rename", response_model=SessionSummaryResponse)
def rename_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    session_id: UUID,
    payload: SessionRenameRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> SessionSummaryResponse:
    return service.rename_session(user, feature, session_id, payload)


@router.patch("/{feature}/sessions/{session_id}/archive", response_model=SessionSummaryResponse)
def archive_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    session_id: UUID,
    payload: SessionArchiveRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> SessionSummaryResponse:
    return service.archive_session(user, feature, session_id, payload)


@router.patch("/{feature}/sessions/{session_id}/pin", response_model=SessionSummaryResponse)
def pin_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    session_id: UUID,
    payload: SessionPinRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> SessionSummaryResponse:
    return service.pin_session(user, feature, session_id, payload)


@router.delete("/{feature}/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    service.delete_session(user, feature, session_id)


@router.post("/{feature}/export", response_model=ChatExportResponse)
def export_chat_session(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    payload: ChatExportRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatExportResponse:
    return service.export_session(user, feature, payload)


@router.patch("/{feature}/messages/{message_id}/bookmark")
def bookmark_message(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    message_id: UUID,
    payload: MessageBookmarkRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
):
    return service.bookmark_message(user, feature, message_id, bookmarked=payload.bookmarked)


@router.delete("/{feature}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_message(
    feature: Annotated[ChatFeatureSlug, Depends(require_supported_chat_feature)],
    message_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    service.delete_message(user, feature, message_id)
