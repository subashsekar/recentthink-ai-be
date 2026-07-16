"""HackerRank agent HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from app.agents.hackerrank.dependencies import get_hackerrank_service
from app.agents.hackerrank.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    DeleteSessionResponse,
    ExportRequest,
    ExportResponse,
    FollowUpRequest,
    FollowUpResponse,
    HackerrankAgentInfoResponse,
    HackerrankExampleResponse,
    HackerrankHistoryListResponse,
    HackerrankModeResponse,
    ManualInputRequiredResponse,
    ProgressResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
    UpdateSessionRequest,
    VersionHistoryItem,
)
from app.agents.hackerrank.service import HackerRankService
from app.core.rate_limit import HACKERRANK_ANALYZE_RATE_LIMIT, HACKERRANK_FOLLOWUP_RATE_LIMIT, limiter
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.schemas.common import ErrorResponse
from app.utils.streaming import should_stream

router = APIRouter(prefix="/hackerrank", tags=["hackerrank"])

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
@limiter.limit(HACKERRANK_ANALYZE_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def analyze_problem(
    request: Request,
    payload: AnalyzeRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> AnalyzeResponse | ManualInputRequiredResponse | StreamingResponse:
    if should_stream(request):
        return StreamingResponse(
            service.analyze_stream(current_user, payload),
            media_type="text/event-stream",
        )
    return await service.analyze(current_user, payload)


@router.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(HACKERRANK_FOLLOWUP_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def follow_up(
    request: Request,
    payload: FollowUpRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> FollowUpResponse:
    _ = request
    return await service.follow_up(current_user, payload)


@router.get(
    "/agents",
    response_model=list[HackerrankAgentInfoResponse],
    responses=_ERROR_RESPONSES,
)
def list_agents(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: HackerRankService = Depends(get_hackerrank_service),
) -> list[HackerrankAgentInfoResponse]:
    return service.list_agents()


@router.get(
    "/history",
    response_model=HackerrankHistoryListResponse,
    responses=_ERROR_RESPONSES,
)
def get_history(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
) -> HackerrankHistoryListResponse:
    return service.list_history(current_user, limit=limit, offset=offset, search=q)


@router.get(
    "/examples",
    response_model=list[HackerrankExampleResponse],
    responses=_ERROR_RESPONSES,
)
def get_examples(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: HackerRankService = Depends(get_hackerrank_service),
) -> list[HackerrankExampleResponse]:
    return service.list_examples()


@router.get(
    "/modes",
    response_model=list[HackerrankModeResponse],
    responses=_ERROR_RESPONSES,
)
def get_modes(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: HackerRankService = Depends(get_hackerrank_service),
) -> list[HackerrankModeResponse]:
    """Return available HackerRank coaching modes."""
    return service.list_modes()


@router.get(
    "/history/{session_id}",
    response_model=SessionDetailResponse,
    responses=_ERROR_RESPONSES,
)
def get_session_history(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> SessionDetailResponse:
    return service.get_session_detail(current_user, session_id)


@router.get(
    "/progress",
    response_model=ProgressResponse,
    responses=_ERROR_RESPONSES,
)
def get_progress(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> ProgressResponse:
    return service.get_progress(current_user)


@router.patch(
    "/history/{session_id}",
    response_model=SessionSummaryResponse,
    responses=_ERROR_RESPONSES,
)
def update_session(
    session_id: UUID,
    payload: UpdateSessionRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> SessionSummaryResponse:
    return service.update_session(current_user, session_id, payload)


@router.delete(
    "/history/{session_id}",
    response_model=DeleteSessionResponse,
    responses=_ERROR_RESPONSES,
)
def delete_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> DeleteSessionResponse:
    service.delete_session(current_user, session_id)
    return DeleteSessionResponse()


@router.get(
    "/sessions/{session_id}/versions",
    response_model=list[VersionHistoryItem],
    responses=_ERROR_RESPONSES,
)
def list_session_versions(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> list[VersionHistoryItem]:
    return service.list_versions(current_user, session_id)


@router.post(
    "/export/markdown",
    response_model=ExportResponse,
    responses=_ERROR_RESPONSES,
)
def export_markdown(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> ExportResponse:
    return service.export(current_user, payload, fmt="markdown")


@router.post(
    "/export/json",
    response_model=ExportResponse,
    responses=_ERROR_RESPONSES,
)
def export_json(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> ExportResponse:
    return service.export(current_user, payload, fmt="json")


@router.post(
    "/export/pdf",
    responses=_ERROR_RESPONSES,
)
def export_pdf(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: HackerRankService = Depends(get_hackerrank_service),
) -> Response:
    result = service.export(current_user, payload, fmt="pdf")
    return Response(
        content=result.content.encode("latin-1"),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
