"""Course Generator / Learning Path HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse

from app.agents.course_generator.dependencies import get_course_generator_service
from app.agents.course_generator.schemas import (
    AdaptiveFeedbackRequest,
    AdaptiveFeedbackResponse,
    BookmarkRequest,
    BookmarkResponse,
    CourseAgentInfoResponse,
    CourseChatHistoryDetailResponse,
    CourseExampleResponse,
    CourseHistoryListResponse,
    DashboardResponse,
    DeleteCourseResponse,
    ExportRequest,
    ExportResponse,
    FollowUpRequest,
    FollowUpResponse,
    GenerateCourseRequest,
    GenerateCourseResponse,
    ProgressResponse,
    SessionDetailResponse,
    UpdateProgressRequest,
    VersionHistoryItem,
)
from app.agents.course_generator.service import CourseGeneratorService
from app.core.rate_limit import COURSE_FOLLOWUP_RATE_LIMIT, COURSE_GENERATE_RATE_LIMIT, limiter
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.schemas.common import ErrorResponse
from app.utils.streaming import should_stream

router = APIRouter(prefix="/courses", tags=["courses"])

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
    response_model=GenerateCourseResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(COURSE_GENERATE_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def generate_course(
    request: Request,
    payload: GenerateCourseRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> GenerateCourseResponse | StreamingResponse:
    if should_stream(request):
        return StreamingResponse(
            service.generate_stream(current_user, payload),
            media_type="text/event-stream",
        )
    return await service.generate(current_user, payload)


@router.post(
    "/follow-up",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(COURSE_FOLLOWUP_RATE_LIMIT)  # type: ignore[untyped-decorator]
async def follow_up(
    request: Request,
    payload: FollowUpRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> FollowUpResponse:
    _ = request
    return await service.follow_up(current_user, payload)


@router.get(
    "/history",
    response_model=CourseHistoryListResponse,
    responses=_ERROR_RESPONSES,
)
def get_history(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
) -> CourseHistoryListResponse:
    return service.list_history(current_user, limit=limit, offset=offset, search=q)


@router.get(
    "/chat-history",
    response_model=CourseHistoryListResponse,
    responses=_ERROR_RESPONSES,
    summary="List course chat history (sidebar)",
)
def list_chat_history(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
) -> CourseHistoryListResponse:
    """Static chat history list — same shape as LeetCode/HackerRank history sidebar."""
    return service.list_history(current_user, limit=limit, offset=offset, search=q)


@router.get(
    "/chat-history/{course_id}",
    response_model=CourseChatHistoryDetailResponse,
    responses=_ERROR_RESPONSES,
    summary="Get course chat history detail",
)
def get_chat_history(
    course_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> CourseChatHistoryDetailResponse:
    """Return saved messages + course snapshot for one history item."""
    return service.get_chat_history(current_user, course_id)


@router.get(
    "/sessions/{session_id}/chat-history",
    response_model=CourseChatHistoryDetailResponse,
    responses=_ERROR_RESPONSES,
    summary="Get chat history by session id",
)
def get_chat_history_by_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> CourseChatHistoryDetailResponse:
    """Mentor-style lookup when the frontend has session_id from generate/follow-up."""
    return service.get_chat_history_by_session(current_user, session_id)


@router.get(
    "/sessions/{session_id}/versions",
    response_model=list[VersionHistoryItem],
    responses=_ERROR_RESPONSES,
)
def list_session_versions(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> list[VersionHistoryItem]:
    """Return assistant message version history for a Course Generator session."""
    return service.list_versions(current_user, session_id)


@router.delete(
    "/chat-history/{course_id}",
    response_model=DeleteCourseResponse,
    responses=_ERROR_RESPONSES,
)
def delete_chat_history(
    course_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> DeleteCourseResponse:
    service.delete_history(current_user, course_id)
    return DeleteCourseResponse()


@router.get(
    "/history/{course_id}",
    response_model=SessionDetailResponse,
    responses=_ERROR_RESPONSES,
)
def get_history_detail(
    course_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> SessionDetailResponse:
    return service.get_history_detail(current_user, course_id)


@router.delete(
    "/history/{course_id}",
    response_model=DeleteCourseResponse,
    responses=_ERROR_RESPONSES,
)
def delete_history(
    course_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> DeleteCourseResponse:
    service.delete_history(current_user, course_id)
    return DeleteCourseResponse()


@router.get(
    "/progress",
    response_model=ProgressResponse,
    responses=_ERROR_RESPONSES,
)
def get_progress(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
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
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> ProgressResponse:
    return service.update_progress(current_user, payload)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    responses=_ERROR_RESPONSES,
)
def get_dashboard(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> DashboardResponse:
    return service.get_dashboard(current_user)


@router.get(
    "/examples",
    response_model=list[CourseExampleResponse],
    responses=_ERROR_RESPONSES,
)
def get_examples(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> list[CourseExampleResponse]:
    return service.list_examples()


@router.get(
    "/agents",
    response_model=list[CourseAgentInfoResponse],
    responses=_ERROR_RESPONSES,
)
def list_agents(
    _current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> list[CourseAgentInfoResponse]:
    return service.list_agents()


@router.post(
    "/adaptive",
    response_model=AdaptiveFeedbackResponse,
    responses=_ERROR_RESPONSES,
)
def adaptive_feedback(
    payload: AdaptiveFeedbackRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> AdaptiveFeedbackResponse:
    return service.adaptive_feedback(current_user, payload)


@router.post(
    "/bookmarks",
    response_model=BookmarkResponse,
    responses=_ERROR_RESPONSES,
)
def add_bookmark(
    payload: BookmarkRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
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
    service: CourseGeneratorService = Depends(get_course_generator_service),
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
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> ExportResponse:
    return service.export(current_user, payload, fmt="json")


@router.post(
    "/export/pdf",
    responses=_ERROR_RESPONSES,
)
def export_pdf(
    payload: ExportRequest,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: CourseGeneratorService = Depends(get_course_generator_service),
) -> Response:
    result = service.export(current_user, payload, fmt="pdf")
    return Response(
        content=result.content.encode("latin-1"),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{result.filename}"'},
    )
