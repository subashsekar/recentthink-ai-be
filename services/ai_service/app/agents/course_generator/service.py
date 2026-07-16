"""Course Generator thin adapter — personalized learning paths via shared AI platform."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import HTTPException, status

from app.agents.course_generator.adapter import (
    build_chat_message,
    build_course_context,
    content_to_markdown,
    course_to_content,
    extract_course_from_chat,
    markdown_to_simple_pdf,
    to_chat_history_detail,
    to_follow_up_response,
    to_generate_response,
    to_history_item,
    to_session_detail,
)
from app.agents.course_generator.agents import CourseAgents
from app.agents.course_generator.catalog import list_examples as catalog_examples
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
from app.coaching.registry import get_mode_registry
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import AIFeature, SessionStatus
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.course_repository import CourseProgressRepository, CourseRepository
from app.schemas.ai import ChatRequest, FollowUpRequest as PlatformFollowUpRequest
from app.services.ai_platform_service import AIPlatformService
from app.utils.sse import format_sse_event
from app.utils.version_history import build_assistant_version_history
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)


class CourseGeneratorService:
    """Thin Learning Path Generator adapter over the shared AI platform."""

    def __init__(
        self,
        *,
        platform_service: AIPlatformService,
        session_repo: AISessionRepository,
        course_repo: CourseRepository,
        progress_repo: CourseProgressRepository,
        message_repo: AIMessageRepository | None = None,
        agents: CourseAgents | None = None,
    ) -> None:
        self._platform = platform_service
        self._sessions = session_repo
        self._courses = course_repo
        self._progress = progress_repo
        self._messages = message_repo
        self._agents = agents or CourseAgents.create_default()

    def list_agents(self) -> list[CourseAgentInfoResponse]:
        return [CourseAgentInfoResponse.model_validate(spec.__dict__) for spec in self._agents.list_specs()]

    async def generate(self, user: AuthenticatedUser, request: GenerateCourseRequest) -> GenerateCourseResponse:
        start = time.perf_counter()
        try:
            resolved_model = self._platform.model_registry.resolve_model_id(
                requested=request.model_id,
                session_model_id=None,
            )
            if not isinstance(resolved_model, str):
                resolved_model = str(resolved_model)
            resolved_mode = request.mode_id
            mode_cfg = get_mode_registry().resolve(resolved_mode)

            context = build_course_context(request)
            if request.prior_response:
                context = {**context, "prior_llm_raw": request.prior_response}
            chat_response = await self._platform.chat(
                user,
                ChatRequest(
                    feature=AIFeature.COURSE_GENERATOR,
                    message=build_chat_message(request),
                    title=f"{request.skill}: {request.goal}",
                    context=context,
                    model=resolved_model,
                    mode_id=resolved_mode,
                    temperature=min(mode_cfg.generation.temperature, 0.35),
                    requested_sections=request.requested_sections,
                ),
            )
            if chat_response.status == SessionStatus.FAILED:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "Course generation failed — the model returned no usable JSON. "
                        "Try another model (deepseek/deepseek-chat or openai/gpt-4o) "
                        "and confirm OpenRouter credits."
                    ),
                )

            content = extract_course_from_chat(chat_response)
            title = content.overview.title or f"{request.skill} Learning Path"
            content_dump = content.model_dump()

            weeks = max(4, request.duration_days // 7)
            if (
                not content.lessons
                and not content.quizzes
                and not content.projects
                and not content.assignments
            ):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "Course generation returned empty content. "
                        "Usually the model output was truncated or invalid JSON. "
                        "Switch model and retry (recommended: deepseek/deepseek-chat or openai/gpt-4o)."
                    ),
                )
            if len(content.lessons) < weeks or not content.quizzes or not content.projects:
                logger.warning(
                    "course_content_sparse",
                    extra={
                        "session_id": str(chat_response.session_id),
                        "lessons": len(content.lessons),
                        "quizzes": len(content.quizzes),
                        "assignments": len(content.assignments),
                        "projects": len(content.projects),
                        "assessments": len(content.assessments),
                        "roadmap_weeks": len(content.roadmap),
                    },
                )

            self._sessions.update_session(
                chat_response.session_id,
                status=SessionStatus.COMPLETED,
                title=title,
                context_metadata=build_course_context(request),
                model_id=resolved_model,
                mode_id=resolved_mode,
            )

            course = self._courses.create(
                user_id=user.user_id,
                session_id=chat_response.session_id,
                title=title,
                request_payload=request.model_dump(),
                content=content_dump,
                overview=content.overview.model_dump(),
                roadmap=[w.model_dump() for w in content.roadmap],
                lessons=[x.model_dump() for x in content.lessons],
                quizzes=[x.model_dump() for x in content.quizzes],
                assignments=[x.model_dump() for x in content.assignments],
                projects=[x.model_dump() for x in content.projects],
                assessments=[x.model_dump() for x in content.assessments],
                resources=[x.model_dump() for x in content.resources],
                learning_tips=list(content.learning_tips),
                next_recommendations=list(content.next_recommendations),
                adaptive=content.adaptive.model_dump(),
                skill=request.skill,
                goal=request.goal,
                level=request.level,
                target_level=request.target_level,
                duration_days=request.duration_days,
                daily_hours=request.daily_hours,
                learning_style=request.learning_style,
                language=request.language,
                programming_language=request.programming_language,
                difficulty=content.overview.difficulty or request.level,
                description=content.overview.description,
            )

            self._progress.record_course_created(
                user.user_id,
                skill=request.skill,
                duration_days=request.duration_days,
                daily_hours=request.daily_hours,
            )

            elapsed = int((time.perf_counter() - start) * 1000)
            response = to_generate_response(chat_response, request, course, mode_id=resolved_mode)
            return response.model_copy(
                update={
                    "usage": response.usage.model_copy(update={"execution_time_ms": elapsed}),
                },
            )
        except Exception as exc:
            logger.error("Course generation failed: %s", exc)
            raise

    async def generate_stream(
        self,
        user: AuthenticatedUser,
        request: GenerateCourseRequest,
    ) -> AsyncIterator[str]:
        """Pseudo-token SSE stream: status/thinking then complete with full response."""
        yield format_sse_event({"type": "status", "status": "thinking"})
        yield format_sse_event({"type": "status", "status": "generating"})
        response = await self.generate(user, request)
        yield format_sse_event({"type": "complete", **response.model_dump(mode="json")})

    async def follow_up(self, user: AuthenticatedUser, request: FollowUpRequest) -> FollowUpResponse:
        session = self._sessions.get_by_id(request.session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{request.session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")

        resolved_model = self._platform.model_registry.resolve_model_id(
            requested=request.model,
            session_model_id=session.model_id,
        )
        resolved_mode = request.mode_id or session.mode_id
        if request.mode_id is not None and resolved_mode != session.mode_id:
            self._sessions.update_session(session.id, mode_id=resolved_mode)

        response = await self._platform.follow_up(
            user,
            PlatformFollowUpRequest(
                session_id=request.session_id,
                question=request.question,
                model=resolved_model,
                mode_id=resolved_mode,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ),
        )
        return to_follow_up_response(response)

    def list_history(
        self,
        user: AuthenticatedUser,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> CourseHistoryListResponse:
        courses = self._courses.list_by_user(user.user_id, limit=limit, offset=offset, search=search)
        total = self._courses.count_by_user(user.user_id)
        page = (offset // limit) + 1 if limit > 0 else 1
        items = []
        for course in courses:
            preview = None
            message_count = 0
            model_id = None
            session = self._sessions.get_by_id(course.session_id)
            if session is not None:
                model_id = session.model_id if isinstance(session.model_id, str) else None
                preview = (session.summary or "")[:180] or None
            if self._messages is not None:
                messages = self._messages.list_by_session(course.session_id, limit=200, offset=0)
                message_count = len(messages)
                if messages and not preview:
                    preview = (messages[-1].content or "")[:180] or None
            items.append(
                to_history_item(
                    course,
                    preview=preview,
                    message_count=message_count,
                    model_id=model_id,
                ),
            )
        return CourseHistoryListResponse(
            items=items,
            page=page,
            page_size=limit,
            total=total,
        )

    def get_history_detail(self, user: AuthenticatedUser, course_id: UUID) -> SessionDetailResponse:
        course = self._require_course_owner(user, course_id)
        detail = self._platform.get_session_detail(user, course.session_id)
        return to_session_detail(detail, course)

    def get_chat_history(self, user: AuthenticatedUser, course_id: UUID) -> CourseChatHistoryDetailResponse:
        """Static chat history for one course (messages + course snapshot)."""
        course = self._require_course_owner(user, course_id)
        detail = self._platform.get_session_detail(user, course.session_id)
        return to_chat_history_detail(detail, course)

    def get_chat_history_by_session(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
    ) -> CourseChatHistoryDetailResponse:
        """Lookup chat history by AI session id (same pattern as mentor history)."""
        session = self._sessions.get_by_id(session_id)
        if session is None or session.feature != AIFeature.COURSE_GENERATOR:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")
        course = self._courses.get_by_session_id(session_id)
        if course is None:
            raise RecordNotFoundError(f"Course for session '{session_id}' not found.")
        detail = self._platform.get_session_detail(user, session_id)
        return to_chat_history_detail(detail, course)

    def delete_history(self, user: AuthenticatedUser, course_id: UUID) -> None:
        course = self._require_course_owner(user, course_id)
        session_id = course.session_id
        self._courses.delete(course.id)
        self._platform.delete_session(user, session_id)

    def get_progress(self, user: AuthenticatedUser) -> ProgressResponse:
        progress = self._progress.get_or_create(user.user_id)
        return ProgressResponse(
            courses_created=progress.courses_created,
            courses_completed=progress.courses_completed,
            lessons_completed=progress.lessons_completed,
            projects_completed=progress.projects_completed,
            quizzes_completed=progress.quizzes_completed,
            current_week=progress.current_week,
            current_lesson=progress.current_lesson,
            completion_pct=progress.completion_pct,
            learning_streak=progress.learning_streak,
            longest_streak=progress.longest_streak,
            study_hours=progress.study_hours,
            favorite_skill=progress.favorite_skill,
            skills=list(progress.skills or []),
            updated_at=progress.updated_at,
        )

    def get_dashboard(self, user: AuthenticatedUser) -> DashboardResponse:
        progress = self.get_progress(user)
        recent = self.list_history(user, limit=5, offset=0)
        active = next((item for item in recent.items if item.completion_pct < 100), None)
        return DashboardResponse(progress=progress, recent_courses=recent.items, active_course=active)

    def update_progress(self, user: AuthenticatedUser, request: UpdateProgressRequest) -> ProgressResponse:
        course = self._require_course_owner(user, request.course_id)
        self._courses.update_progress(
            course.id,
            current_week=request.current_week,
            current_lesson=request.current_lesson,
            lessons_completed_delta=request.lessons_completed_delta,
            quizzes_completed_delta=request.quizzes_completed_delta,
            projects_completed_delta=request.projects_completed_delta,
            study_hours_delta=request.study_hours_delta,
            completion_pct=request.completion_pct,
            mark_completed=request.mark_completed,
        )
        self._progress.apply_deltas(
            user.user_id,
            lessons_completed_delta=request.lessons_completed_delta,
            quizzes_completed_delta=request.quizzes_completed_delta,
            projects_completed_delta=request.projects_completed_delta,
            study_hours_delta=request.study_hours_delta,
            current_week=request.current_week,
            current_lesson=request.current_lesson,
            completion_pct=request.completion_pct,
            mark_course_completed=request.mark_completed,
        )
        return self.get_progress(user)

    def adaptive_feedback(self, user: AuthenticatedUser, request: AdaptiveFeedbackRequest) -> AdaptiveFeedbackResponse:
        course = self._require_course_owner(user, request.course_id)
        content = course_to_content(course)
        adaptive = content.adaptive
        if request.score_pct < 50:
            performance = "struggling"
            recommendations = list(adaptive.struggling) or [
                "Review the previous lesson with simplified examples",
                "Complete extra practice exercises for this topic",
                "Re-read concept explanations before advancing",
            ]
            return AdaptiveFeedbackResponse(
                course_id=course.id,
                performance=performance,
                recommendations=recommendations,
                unlock_advanced=False,
                skip_basics=False,
            )
        if request.score_pct >= 85:
            performance = "excelling"
            recommendations = list(adaptive.excelling) or [
                "Skip repeated basics for this topic",
                "Unlock advanced content for the next week",
                "Attempt a larger project challenge",
            ]
            return AdaptiveFeedbackResponse(
                course_id=course.id,
                performance=performance,
                recommendations=recommendations,
                unlock_advanced=True,
                skip_basics=True,
            )
        return AdaptiveFeedbackResponse(
            course_id=course.id,
            performance="on_track",
            recommendations=["Continue with the next scheduled lesson"],
            unlock_advanced=False,
            skip_basics=False,
        )

    def add_bookmark(self, user: AuthenticatedUser, request: BookmarkRequest) -> BookmarkResponse:
        course = self._require_course_owner(user, request.course_id)
        bookmark = self._courses.add_bookmark(
            user_id=user.user_id,
            course_id=course.id,
            item_type=request.item_type,
            item_id=request.item_id,
            title=request.title,
        )
        return BookmarkResponse(
            id=bookmark.id,
            course_id=bookmark.course_id,
            item_type=bookmark.item_type,
            item_id=bookmark.item_id,
            title=bookmark.title,
            created_at=bookmark.created_at,
        )

    def list_examples(self) -> list[CourseExampleResponse]:
        return catalog_examples()

    def export(self, user: AuthenticatedUser, request: ExportRequest, *, fmt: str) -> ExportResponse:
        course = self._require_course_owner(user, request.course_id)
        content = course_to_content(course)
        safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in course.title)[:60] or "course"

        if fmt == "json":
            payload = content.model_dump()
            if request.include:
                # Keep overview always; filter top-level sections.
                filtered = {"overview": payload.get("overview")}
                mapping = {
                    "roadmap": "roadmap",
                    "lessons": "lessons",
                    "projects": "projects",
                    "assignments": "assignments",
                    "quiz": "quizzes",
                    "assessment": "assessments",
                    "resources": "resources",
                }
                for key in request.include:
                    target = mapping.get(key, key)
                    if target in payload:
                        filtered[target] = payload[target]
                payload = filtered
            body = json.dumps(payload, indent=2, default=str)
            return ExportResponse(
                course_id=course.id,
                format="json",
                filename=f"{safe_title}.json",
                content=body,
                content_type="application/json",
            )

        markdown = content_to_markdown(content, include=request.include)
        if fmt == "markdown":
            return ExportResponse(
                course_id=course.id,
                format="markdown",
                filename=f"{safe_title}.md",
                content=markdown,
                content_type="text/markdown",
            )

        # PDF: return base64-friendly latin-1 text of minimal PDF bytes as latin-1 string
        pdf_bytes = markdown_to_simple_pdf(markdown, title=course.title)
        return ExportResponse(
            course_id=course.id,
            format="pdf",
            filename=f"{safe_title}.pdf",
            content=pdf_bytes.decode("latin-1"),
            content_type="application/pdf",
        )

    def _require_course_owner(self, user: AuthenticatedUser, course_id: UUID):
        course = self._courses.get_by_id(course_id)
        if course is None:
            raise RecordNotFoundError(f"Course '{course_id}' not found.")
        if not can_access_session(user, course.user_id):
            raise ForbiddenError("You do not have access to this course.")
        return course

    def list_versions(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
    ) -> list[VersionHistoryItem]:
        if self._messages is None:
            raise RuntimeError("Message repository is not configured.")
        ai_session_id = self._resolve_ai_session_id(user, session_id)
        records = build_assistant_version_history(self._messages.list_all_by_session(ai_session_id))
        return [VersionHistoryItem.model_validate(record.__dict__) for record in records]

    def _resolve_ai_session_id(self, user: AuthenticatedUser, session_id: UUID) -> UUID:
        session = self._sessions.get_by_id(session_id)
        if session is not None and session.feature == AIFeature.COURSE_GENERATOR:
            if not can_access_session(user, session.user_id):
                raise ForbiddenError("You do not have access to this session.")
            return session.id
        course = self._courses.get_by_id(session_id)
        if course is not None:
            if not can_access_session(user, course.user_id):
                raise ForbiddenError("You do not have access to this course.")
            return course.session_id
        raise RecordNotFoundError(f"Session '{session_id}' not found.")
