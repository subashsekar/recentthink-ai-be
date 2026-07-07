"""LeetCode agent HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from app.agents.leetcode.dependencies import get_leetcode_service
from app.agents.leetcode.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    DeleteSessionResponse,
    FollowUpRequest,
    FollowUpResponse,
    LeetCodeAgentInfoResponse,
    ManualInputRequiredResponse,
    ProgressResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
)
from app.agents.leetcode.service import LeetCodeService
from app.core.rate_limit import (
    LEETCODE_ANALYZE_RATE_LIMIT,
    LEETCODE_FOLLOWUP_RATE_LIMIT,
    limiter,
)
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.schemas.common import ErrorResponse
from fastapi import APIRouter, Depends, Request, status

router = APIRouter(prefix="/leetcode", tags=["leetcode"])

_ERROR_RESPONSES: dict[int | str, dict[str, type[ErrorResponse]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


@router.post(
    "/analyze",
    response_model=AnalyzeResponse | ManualInputRequiredResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(LEETCODE_ANALYZE_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def analyze_problem(
    request: Request,
    payload: AnalyzeRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> AnalyzeResponse | ManualInputRequiredResponse:
    """Analyze a LeetCode problem via the shared single-LLM workflow."""
    return await leetcode_service.analyze(current_user, payload)


@router.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(LEETCODE_FOLLOWUP_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def follow_up(
    request: Request,
    payload: FollowUpRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> FollowUpResponse:
    """Ask a follow-up question in an existing LeetCode session."""
    return await leetcode_service.follow_up(current_user, payload)


@router.get(
    "/agents",
    response_model=list[LeetCodeAgentInfoResponse],
    responses=_ERROR_RESPONSES,
)
def list_agents(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> list[LeetCodeAgentInfoResponse]:
    """List the five declared LeetCode pipeline agents."""
    _ = current_user
    return leetcode_service.list_agents()


@router.get(
    "/history",
    response_model=list[SessionSummaryResponse],
    responses=_ERROR_RESPONSES,
)
def get_history(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
    limit: int = 50,
    offset: int = 0,
) -> list[SessionSummaryResponse]:
    """Return the authenticated user's LeetCode session history."""
    return leetcode_service.list_history(current_user, limit=limit, offset=offset)


@router.get(
    "/history/{session_id}",
    response_model=SessionDetailResponse,
    responses=_ERROR_RESPONSES,
)
def get_session_history(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> SessionDetailResponse:
    """Return the full conversation for a session."""
    return leetcode_service.get_session_detail(current_user, session_id)


@router.get(
    "/progress",
    response_model=ProgressResponse,
    responses=_ERROR_RESPONSES,
)
def get_progress(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> ProgressResponse:
    """Return the user's LeetCode practice progress."""
    return leetcode_service.get_progress(current_user)


@router.delete(
    "/history/{session_id}",
    response_model=DeleteSessionResponse,
    responses=_ERROR_RESPONSES,
)
def delete_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    leetcode_service: LeetCodeService = Depends(get_leetcode_service),
) -> DeleteSessionResponse:
    """Delete a LeetCode session and its conversation history."""
    leetcode_service.delete_session(current_user, session_id)
    return DeleteSessionResponse()
