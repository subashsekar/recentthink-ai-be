"""HackerRank thin adapter — challenge fetch, platform workflow, progress."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from uuid import UUID

from app.agents.hackerrank.adapter import (
    build_chat_message,
    build_problem_context,
    to_analyze_response,
    to_follow_up_response,
    to_history_item,
    to_session_detail,
    to_session_summary,
)
from app.agents.hackerrank.agents import HackerrankAgents
from app.agents.hackerrank.catalog import list_examples as catalog_examples
from app.agents.hackerrank.problem_fetcher import HackerrankProblemFetcher
from app.agents.hackerrank.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FollowUpRequest,
    FollowUpResponse,
    HackerrankAgentInfoResponse,
    HackerrankExampleResponse,
    HackerrankHistoryListResponse,
    ManualInputRequiredResponse,
    ProblemData,
    ProgressResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
    UpdateSessionRequest,
)
from app.coaching.registry import get_mode_registry
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import AIFeature, SessionStatus
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.hackerrank_progress_repository import HackerrankProgressRepository
from app.schemas.ai import ChatRequest, FollowUpRequest as PlatformFollowUpRequest
from app.services.ai_platform_service import AIPlatformService
from app.utils.sse import format_sse_event
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)

MANUAL_INPUT_INSTRUCTIONS = [
    "Copy the full problem statement from HackerRank.",
    "Paste it in the problem_statement field when calling POST /hackerrank/analyze.",
    "Optionally include the problem title in the title field.",
]


class HackerRankService:
    """Thin HackerRank adapter over the shared AI platform."""

    def __init__(
        self,
        *,
        platform_service: AIPlatformService,
        session_repo: AISessionRepository,
        progress_repo: HackerrankProgressRepository,
        agents: HackerrankAgents | None = None,
        problem_fetcher: HackerrankProblemFetcher | None = None,
    ) -> None:
        self._platform = platform_service
        self._sessions = session_repo
        self._progress = progress_repo
        self._agents = agents or HackerrankAgents.create_default()
        self._fetcher = problem_fetcher or self._agents.problem_fetcher

    def list_agents(self) -> list[HackerrankAgentInfoResponse]:
        return [HackerrankAgentInfoResponse.model_validate(spec.__dict__) for spec in self._agents.list_specs()]

    async def analyze(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> AnalyzeResponse | ManualInputRequiredResponse:
        problem, manual_required = await self._resolve_problem(request)
        if manual_required:
            return self._manual_required_response(user, request)
        assert problem is not None
        return await self._run_analysis(user, problem, request)

    async def analyze_stream(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> AsyncIterator[str]:
        problem, manual_required = await self._resolve_problem(request)
        if manual_required:
            response = self._manual_required_response(user, request)
            yield format_sse_event({"type": "complete", **response.model_dump(mode="json")})
            return

        assert problem is not None
        yield format_sse_event(
            {
                "type": "problem_statement",
                "problem_statement_markdown": problem.problem_statement_markdown or "",
            },
        )
        response = await self._run_analysis(user, problem, request)
        yield format_sse_event({"type": "complete", **response.model_dump(mode="json")})

    def _manual_required_response(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> ManualInputRequiredResponse:
        model_id = None
        mode_id = None
        if request.model_id is not None:
            self._platform.model_registry.validate_model_id(request.model_id)
            model_id = request.model_id
        if request.mode_id is not None:
            mode_id = request.mode_id
        session = self._sessions.create_session(
            user_id=user.user_id,
            feature=AIFeature.HACKERRANK,
            title=request.title,
            status=SessionStatus.MANUAL_REQUIRED,
            context_metadata={
                "problem_url": str(request.problem_url) if request.problem_url else None,
            },
        )
        updates: dict[str, object] = {}
        if model_id is not None:
            updates["model_id"] = model_id
        if mode_id is not None:
            updates["mode_id"] = mode_id
        if updates:
            self._sessions.update_session(session.id, **updates)
        return ManualInputRequiredResponse(
            session_id=session.id,
            status=SessionStatus.MANUAL_REQUIRED,
            message=(
                "We could not retrieve the challenge from the provided URL. "
                "Please paste the problem statement manually."
            ),
            instructions=MANUAL_INPUT_INSTRUCTIONS,
        )

    async def _run_analysis(
        self,
        user: AuthenticatedUser,
        problem: ProblemData,
        request: AnalyzeRequest,
    ) -> AnalyzeResponse:
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
            context = build_problem_context(problem)
            if request.prior_response:
                context = {**context, "prior_llm_raw": request.prior_response}
            chat_response = await self._platform.chat(
                user,
                ChatRequest(
                    feature=AIFeature.HACKERRANK,
                    message=build_chat_message(problem),
                    title=problem.title,
                    context=context,
                    model=resolved_model,
                    mode_id=resolved_mode,
                    temperature=mode_cfg.generation.temperature,
                    requested_sections=request.requested_sections,
                ),
            )
            if chat_response.status == SessionStatus.FAILED:
                raise RuntimeError("HackerRank analysis workflow failed.")

            planner_meta = chat_response.planner.metadata or {}
            difficulty = planner_meta.get("difficulty") or problem.difficulty or "Unknown"
            category = planner_meta.get("problem_category") or problem.domain or (
                problem.topics[0] if problem.topics else problem.title
            )
            self._sessions.update_session(
                chat_response.session_id,
                status=SessionStatus.COMPLETED,
                title=problem.title,
                context_metadata=build_problem_context(problem),
                model_id=resolved_model,
                mode_id=resolved_mode,
            )

            primary_language = None
            coder_module = next((m for m in chat_response.modules if m.module.value == "coder"), None)
            if coder_module and coder_module.metadata and coder_module.metadata.get("language"):
                primary_language = str(coder_module.metadata.get("language"))

            self._progress.record_attempt(
                user.user_id,
                difficulty=str(difficulty),
                category=str(category),
                domain=problem.domain,
                language=primary_language,
                tags=problem.tags,
                completed=True,
            )

            elapsed = int((time.perf_counter() - start) * 1000)
            response = to_analyze_response(chat_response, problem, mode_id=resolved_mode)
            return response.model_copy(update={"total_execution_time_ms": elapsed})
        except Exception as exc:
            logger.error("HackerRank analysis failed: %s", exc)
            raise

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

    def update_session(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        request: UpdateSessionRequest,
    ) -> SessionSummaryResponse:
        session = self._sessions.get_by_id(session_id)
        if session is None or session.feature != AIFeature.HACKERRANK:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")

        updates: dict[str, object] = {}
        if request.model_id is not None:
            self._platform.model_registry.validate_model_id(request.model_id)
            updates["model_id"] = request.model_id
        if request.mode_id is not None:
            updates["mode_id"] = request.mode_id
        updated = self._sessions.update_session(session_id, **updates)
        return to_session_summary(updated)

    async def _resolve_problem(self, request: AnalyzeRequest) -> tuple[ProblemData | None, bool]:
        if request.problem_statement:
            title = request.title or "Manual Challenge"
            slug = None
            if request.problem_url:
                from app.utils.hackerrank_url import extract_hackerrank_slug

                try:
                    slug = extract_hackerrank_slug(str(request.problem_url))
                except ValueError:
                    slug = None
            return (
                self._fetcher.build_from_manual_input(
                    title=title,
                    statement=request.problem_statement,
                    slug=slug,
                    url=str(request.problem_url) if request.problem_url else None,
                ),
                False,
            )

        if request.problem_url:
            result = await self._fetcher.fetch_from_url(str(request.problem_url))
            if result.success and result.problem:
                return result.problem, False
            return None, True

        return None, True

    def list_history(
        self,
        user: AuthenticatedUser,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> HackerrankHistoryListResponse:
        if user.role in {"ADMIN", "SUPER_ADMIN"}:
            sessions = self._sessions.list_all(
                feature=AIFeature.HACKERRANK,
                search=search,
                limit=limit,
                offset=offset,
            )
            total = len(sessions)
        else:
            sessions = self._sessions.list_by_user(
                user.user_id,
                feature=AIFeature.HACKERRANK,
                search=search,
                limit=limit,
                offset=offset,
            )
            total = self._sessions.count_by_user(user.user_id, feature=AIFeature.HACKERRANK)

        page = (offset // limit) + 1 if limit > 0 else 1
        return HackerrankHistoryListResponse(
            items=[to_history_item(session) for session in sessions],
            page=page,
            page_size=limit,
            total=total,
        )

    def list_examples(self) -> list[HackerrankExampleResponse]:
        return catalog_examples()

    def get_session_detail(self, user: AuthenticatedUser, session_id: UUID) -> SessionDetailResponse:
        detail = self._platform.get_session_detail(user, session_id)
        return to_session_detail(detail)

    def delete_session(self, user: AuthenticatedUser, session_id: UUID) -> None:
        self._platform.delete_session(user, session_id)

    def get_progress(self, user: AuthenticatedUser) -> ProgressResponse:
        progress = self._progress.get_or_create(user.user_id)
        return ProgressResponse(
            problems_attempted=progress.problems_attempted,
            problems_completed=progress.problems_completed,
            easy_count=progress.easy_count,
            medium_count=progress.medium_count,
            hard_count=progress.hard_count,
            current_streak=progress.current_streak,
            longest_streak=progress.longest_streak,
            favorite_pattern=progress.favorite_pattern,
            weak_topics=list(progress.weak_topics or []),
            strong_topics=list(progress.strong_topics or []),
            updated_at=progress.updated_at,
        )
