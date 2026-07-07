"""Generic AI platform HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.rate_limit import AI_CHAT_RATE_LIMIT, limiter
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_ai_platform_service
from app.models.enums import AIFeature
from app.schemas.ai import (
    ChatRequest,
    ChatResponse,
    FollowUpRequest,
    FollowUpResponse,
    HistoryListResponse,
    ModelsResponse,
    SessionDetailResponse,
    SummarizeResponse,
)
from app.services.ai_platform_service import AIPlatformService

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(AI_CHAT_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def chat(
    request: Request,
    payload: ChatRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> ChatResponse:
    """Run the generic single-LLM AI pipeline for any feature."""
    return await service.chat(user, payload)


@router.get("/history", response_model=HistoryListResponse)
def list_history(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
    feature: AIFeature | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> HistoryListResponse:
    """List AI session history for the authenticated user."""
    return service.list_history(user, feature=feature, search=search, limit=limit, offset=offset)


@router.get("/history/{session_id}", response_model=SessionDetailResponse)
def get_session_history(
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> SessionDetailResponse:
    """Return full conversation history for a session."""
    return service.get_session_detail(user, session_id, limit=limit, offset=offset)


@router.delete("/history/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_history(
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> None:
    """Delete an AI session and its history."""
    service.delete_session(user, session_id)


@router.get("/models", response_model=ModelsResponse)
def list_models(
    _user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> ModelsResponse:
    """List configured LLM models."""
    return service.list_models()


@router.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
)
async def follow_up(
    payload: FollowUpRequest,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> FollowUpResponse:
    """Handle a follow-up question using existing session context."""
    return await service.follow_up(user, payload)


@router.post(
    "/session/{session_id}/summarize",
    response_model=SummarizeResponse,
    status_code=status.HTTP_200_OK,
)
async def summarize_session(
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> SummarizeResponse:
    """Generate a conversation summary for the session."""
    return await service.summarize_session(user, session_id)


@router.delete("/memory/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_memory(
    session_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AIPlatformService, Depends(get_ai_platform_service)],
) -> None:
    """Clear conversation memory for a session."""
    service.clear_memory(user, session_id)
