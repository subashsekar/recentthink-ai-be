"""LeetCode thin adapter — problem fetch, platform workflow, progress."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from uuid import UUID

from app.agents.leetcode.agents import LeetCodeAgents
from app.agents.leetcode.adapter import (
    build_chat_message,
    build_problem_context,
    to_analyze_response,
    to_follow_up_response,
    to_session_detail,
    to_session_summary,
)
from app.agents.leetcode.problem_fetcher import LeetCodeProblemFetcher
from app.agents.leetcode.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FollowUpRequest,
    FollowUpResponse,
    ManualInputRequiredResponse,
    ProblemData,
    ProgressResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
    LeetCodeAgentInfoResponse,
)
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, SessionStatus
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.leetcode_progress_repository import LeetCodeProgressRepository
from app.schemas.ai import ChatRequest, FollowUpRequest as PlatformFollowUpRequest
from app.services.ai_platform_service import AIPlatformService
from app.utils.sse import format_sse_event
from shared.logging import get_logger

logger = get_logger(__name__)

MANUAL_INPUT_INSTRUCTIONS = [
    "Copy the full problem statement from LeetCode.",
    "Paste it in the problem_statement field when calling POST /leetcode/analyze.",
    "Optionally include the problem title in the title field.",
    "You may also upload a screenshot separately in a future release.",
]


class LeetCodeService:
    """Thin LeetCode adapter over the shared AI platform."""

    def __init__(
        self,
        *,
        platform_service: AIPlatformService,
        session_repo: AISessionRepository,
        progress_repo: LeetCodeProgressRepository,
        agents: LeetCodeAgents | None = None,
        problem_fetcher: LeetCodeProblemFetcher | None = None,
    ) -> None:
        self._platform = platform_service
        self._sessions = session_repo
        self._progress = progress_repo
        self._agents = agents or LeetCodeAgents.create_default()
        self._fetcher = problem_fetcher or self._agents.problem_fetcher

    def list_agents(self) -> list[LeetCodeAgentInfoResponse]:
        """Return declarations for the five LeetCode pipeline agents."""
        return [
            LeetCodeAgentInfoResponse.model_validate(spec.model_dump())
            for spec in self._agents.list_specs()
        ]

    async def analyze(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> AnalyzeResponse | ManualInputRequiredResponse:
        """Fetch problem context and run the shared single-LLM workflow."""
        problem, manual_required = await self._resolve_problem(request)
        if manual_required:
            return self._manual_required_response(user, request)
        assert problem is not None
        return await self._run_analysis(user, problem)

    async def analyze_stream(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> AsyncIterator[str]:
        """Stream problem statement markdown, then the full analysis result."""
        problem, manual_required = await self._resolve_problem(request)
        if manual_required:
            response = self._manual_required_response(user, request)
            yield format_sse_event(
                {"type": "complete", **response.model_dump(mode="json")},
            )
            return

        assert problem is not None
        yield format_sse_event(
            {
                "type": "problem_statement",
                "problem_statement_markdown": problem.problem_statement_markdown or "",
            },
        )
        response = await self._run_analysis(user, problem)
        yield format_sse_event(
            {"type": "complete", **response.model_dump(mode="json")},
        )

    def _manual_required_response(
        self,
        user: AuthenticatedUser,
        request: AnalyzeRequest,
    ) -> ManualInputRequiredResponse:
        session = self._sessions.create_session(
            user_id=user.user_id,
            feature=AIFeature.LEETCODE,
            title=request.title,
            status=SessionStatus.MANUAL_REQUIRED,
            context_metadata={
                "problem_url": str(request.problem_url) if request.problem_url else None,
            },
        )
        return ManualInputRequiredResponse(
            session_id=session.id,
            status=SessionStatus.MANUAL_REQUIRED,
            message=(
                "We could not retrieve the problem from the provided URL. "
                "Please paste the problem statement manually."
            ),
            instructions=MANUAL_INPUT_INSTRUCTIONS,
        )

    async def _run_analysis(
        self,
        user: AuthenticatedUser,
        problem: ProblemData,
    ) -> AnalyzeResponse:
        start = time.perf_counter()
        try:
            chat_response = await self._platform.chat(
                user,
                ChatRequest(
                    feature=AIFeature.LEETCODE,
                    message=build_chat_message(problem),
                    title=problem.title,
                    context=build_problem_context(problem),
                ),
            )
            if chat_response.status == SessionStatus.FAILED:
                raise RuntimeError("LeetCode analysis workflow failed.")

            planner_meta = chat_response.planner.metadata or {}
            difficulty = planner_meta.get("difficulty") or problem.difficulty or "Unknown"
            category = planner_meta.get("problem_category") or (
                problem.topics[0] if problem.topics else problem.title
            )
            self._sessions.update_session(
                chat_response.session_id,
                status=SessionStatus.COMPLETED,
                title=problem.title,
                context_metadata=build_problem_context(problem),
            )
            self._progress.record_attempt(
                user.user_id,
                difficulty=str(difficulty),
                category=str(category),
                completed=True,
            )

            elapsed = int((time.perf_counter() - start) * 1000)
            response = to_analyze_response(chat_response, problem)
            return response.model_copy(update={"total_execution_time_ms": elapsed})
        except Exception as exc:
            logger.error("LeetCode analysis failed: %s", exc)
            raise

    async def follow_up(
        self,
        user: AuthenticatedUser,
        request: FollowUpRequest,
    ) -> FollowUpResponse:
        """Handle a follow-up question in an existing LeetCode session."""
        response = await self._platform.follow_up(
            user,
            PlatformFollowUpRequest(
                session_id=request.session_id,
                question=request.question,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ),
        )
        return to_follow_up_response(response)

    async def _resolve_problem(
        self,
        request: AnalyzeRequest,
    ) -> tuple[ProblemData | None, bool]:
        if request.problem_statement:
            title = request.title or "Manual Problem"
            slug = None
            if request.problem_url:
                from app.utils.leetcode_url import extract_leetcode_slug

                try:
                    slug = extract_leetcode_slug(str(request.problem_url))
                except ValueError:
                    slug = None
            return (
                self._fetcher.build_from_manual_input(
                    title=title,
                    statement=request.problem_statement,
                    slug=slug,
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
    ) -> list[SessionSummaryResponse]:
        if user.role in {"ADMIN", "SUPER_ADMIN"}:
            sessions = self._sessions.list_all(
                feature=AIFeature.LEETCODE,
                search=search,
                limit=limit,
                offset=offset,
            )
        else:
            sessions = self._sessions.list_by_user(
                user.user_id,
                feature=AIFeature.LEETCODE,
                search=search,
                limit=limit,
                offset=offset,
            )
        return [to_session_summary(session) for session in sessions]

    def get_session_detail(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
    ) -> SessionDetailResponse:
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
