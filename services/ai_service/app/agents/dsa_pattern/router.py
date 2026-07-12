"""DSA Pattern Coach HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.agents.dsa_pattern.dependencies import get_dsa_pattern_service
from app.agents.dsa_pattern.schemas import (
    BookmarkRequest,
    BookmarkResponse,
    DashboardResponse,
    DeletePatternResponse,
    ExportRequest,
    ExportResponse,
    FollowUpRequest,
    FollowUpResponse,
    GeneratePatternRequest,
    GeneratePatternResponse,
    PatternAgentInfoResponse,
    PatternExampleResponse,
    PatternHistoryListResponse,
    ProgressResponse,
    SessionDetailResponse,
    UpdateProgressRequest,
)
from app.agents.dsa_pattern.service import DsaPatternService
from app.core.rate_limit import DSA_PATTERN_FOLLOWUP_RATE_LIMIT, DSA_PATTERN_GENERATE_RATE_LIMIT, limiter
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/dsa-pattern", tags=["dsa-pattern"])

_ERROR_RESPONSES: dict[int | str, dict[str, type[ErrorResponse]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


@router.post(
    "/generate",
    response_model=GeneratePatternResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(DSA_PATTERN_GENERATE_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def generate_pattern(
    request: Request,
    payload: GeneratePatternRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> GeneratePatternResponse:
    _ = request
    return await service.generate(current_user, payload)


@router.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(DSA_PATTERN_FOLLOWUP_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def follow_up(
    request: Request,
    payload: FollowUpRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> FollowUpResponse:
    _ = request
    return await service.follow_up(current_user, payload)


@router.get(
    "/history",
    response_model=PatternHistoryListResponse,
    responses=_ERROR_RESPONSES,
)
def get_history(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
) -> PatternHistoryListResponse:
    return service.list_history(current_user, limit=limit, offset=offset, search=q)


@router.get(
    "/history/{session_id}",
    response_model=SessionDetailResponse,
    responses=_ERROR_RESPONSES,
)
def get_history_detail(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> SessionDetailResponse:
    return service.get_history_detail(current_user, session_id)


@router.delete(
    "/history/{session_id}",
    response_model=DeletePatternResponse,
    responses=_ERROR_RESPONSES,
)
def delete_history(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> DeletePatternResponse:
    service.delete_history(current_user, session_id)
    return DeletePatternResponse()


@router.get(
    "/progress",
    response_model=ProgressResponse,
    responses=_ERROR_RESPONSES,
)
def get_progress(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> ProgressResponse:
    return service.get_progress(current_user)


@router.post(
    "/progress",
    response_model=ProgressResponse,
    responses=_ERROR_RESPONSES,
)
def update_progress(
    payload: UpdateProgressRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> ProgressResponse:
    return service.update_progress(current_user, payload)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    responses=_ERROR_RESPONSES,
)
def get_dashboard(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> DashboardResponse:
    return service.get_dashboard(current_user)


@router.get(
    "/examples",
    response_model=list[PatternExampleResponse],
    responses=_ERROR_RESPONSES,
)
def get_examples(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> list[PatternExampleResponse]:
    return service.list_examples()


@router.get(
    "/agents",
    response_model=list[PatternAgentInfoResponse],
    responses=_ERROR_RESPONSES,
)
def list_agents(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> list[PatternAgentInfoResponse]:
    return service.list_agents()


@router.post(
    "/bookmarks",
    response_model=BookmarkResponse,
    responses=_ERROR_RESPONSES,
)
def add_bookmark(
    payload: BookmarkRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> BookmarkResponse:
    return service.add_bookmark(current_user, payload)


@router.post(
    "/export/markdown",
    response_model=ExportResponse,
    responses=_ERROR_RESPONSES,
)
def export_markdown(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
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
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> ExportResponse:
    return service.export(current_user, payload, fmt="json")


@router.post(
    "/export/pdf",
    responses=_ERROR_RESPONSES,
)
def export_pdf(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: DsaPatternService = Depends(get_dsa_pattern_service),
) -> Response:
    result = service.export(current_user, payload, fmt="pdf")
    return Response(
        content=result.content.encode("latin-1"),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
