"""DSA Pattern Coach thin adapter — pattern-centric learning via shared AI platform."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.agents.dsa_pattern.adapter import (
    build_chat_message,
    build_pattern_context,
    content_to_markdown,
    extract_pattern_from_chat,
    markdown_to_simple_pdf,
    pattern_to_content,
    to_follow_up_response,
    to_generate_response,
    to_history_item,
    to_session_detail,
)
from app.agents.dsa_pattern.agents import PatternAgents
from app.agents.dsa_pattern.catalog import list_examples as catalog_examples
from app.agents.dsa_pattern.schemas import (
    BookmarkRequest,
    BookmarkResponse,
    DashboardResponse,
    ExportRequest,
    ExportResponse,
    FollowUpRequest,
    FollowUpResponse,
    GeneratePatternRequest,
    GeneratePatternResponse,
    MasteryItem,
    PatternAgentInfoResponse,
    PatternExampleResponse,
    PatternHistoryListResponse,
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
from app.repositories.dsa_pattern_repository import PatternProgressRepository, PatternSessionRepository
from app.schemas.ai import ChatRequest, FollowUpRequest as PlatformFollowUpRequest
from app.services.ai_platform_service import AIPlatformService
from app.utils.sse import format_sse_event
from app.utils.version_history import build_assistant_version_history
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)


def _pattern_content_is_usable(content: Any) -> bool:
    """True when the LLM filled core pattern sections (not empty schema defaults)."""
    overview = content.overview
    if str(getattr(overview, "definition", "") or "").strip():
        return True
    if str(getattr(content.mental_model, "summary", "") or "").strip():
        return True
    recognition = content.recognition
    if getattr(recognition, "keywords", None) or getattr(recognition, "checklist", None):
        return True
    if content.templates:
        return True
    if str(getattr(content.easy_example, "title", "") or "").strip():
        return True
    practice = content.practice
    if getattr(practice, "easy", None) or getattr(practice, "roadmap", None):
        return True
    quiz = content.quiz
    if getattr(quiz, "mcqs", None) or getattr(quiz, "flashcards", None):
        return True
    return False


class DsaPatternService:
    """Thin DSA Pattern Coach adapter over the shared AI platform."""

    def __init__(
        self,
        *,
        platform_service: AIPlatformService,
        session_repo: AISessionRepository,
        pattern_repo: PatternSessionRepository,
        progress_repo: PatternProgressRepository,
        message_repo: AIMessageRepository | None = None,
        agents: PatternAgents | None = None,
    ) -> None:
        self._platform = platform_service
        self._sessions = session_repo
        self._patterns = pattern_repo
        self._progress = progress_repo
        self._messages = message_repo
        self._agents = agents or PatternAgents.create_default()

    def list_agents(self) -> list[PatternAgentInfoResponse]:
        return [PatternAgentInfoResponse.model_validate(spec.__dict__) for spec in self._agents.list_specs()]

    async def generate(self, user: AuthenticatedUser, request: GeneratePatternRequest) -> GeneratePatternResponse:
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

            context = build_pattern_context(request)
            if request.prior_response:
                context = {**context, "prior_llm_raw": request.prior_response}
            chat_response = await self._platform.chat(
                user,
                ChatRequest(
                    feature=AIFeature.DSA_PATTERN,
                    message=build_chat_message(request),
                    title=f"DSA Pattern: {request.pattern}",
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
                        "DSA pattern generation failed — the model returned no usable JSON. "
                        "Try another model (e.g. deepseek/deepseek-chat or openai/gpt-4o) "
                        "and confirm OpenRouter credits."
                    ),
                )

            content = extract_pattern_from_chat(chat_response)
            if not _pattern_content_is_usable(content):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(
                        "DSA pattern generation returned empty lesson content. "
                        "Usually the model output was truncated or invalid JSON. "
                        "Switch model in the dropdown and retry "
                        "(recommended: deepseek/deepseek-chat or openai/gpt-4o)."
                    ),
                )
            title = content.overview.pattern or request.pattern
            if title and not title.lower().startswith("dsa"):
                title = f"{request.pattern} Pattern Coach"
            content_dump = content.model_dump()
            next_pattern = content.next_pattern_recommendation.pattern or None

            self._sessions.update_session(
                chat_response.session_id,
                status=SessionStatus.COMPLETED,
                title=title,
                context_metadata=build_pattern_context(request),
                model_id=resolved_model,
                mode_id=resolved_mode,
            )

            pattern_session = self._patterns.create(
                user_id=user.user_id,
                session_id=chat_response.session_id,
                title=title,
                pattern_name=request.pattern,
                request_payload=request.model_dump(),
                content=content_dump,
                overview=content.overview.model_dump(),
                mental_model=content.mental_model.model_dump(),
                recognition=content.recognition.model_dump(),
                visualization=content.visualization.model_dump(),
                templates=[t.model_dump() for t in content.templates],
                easy_example=content.easy_example.model_dump(),
                medium_example=content.medium_example.model_dump(),
                hard_example=content.hard_example.model_dump(),
                common_mistakes=list(content.common_mistakes),
                interview_tips=content.interview_tips.model_dump(),
                pattern_comparison=[c.model_dump() for c in content.pattern_comparison],
                practice=content.practice.model_dump(),
                quiz=content.quiz.model_dump(),
                next_pattern_recommendation=content.next_pattern_recommendation.model_dump(),
                level=request.level,
                language=request.language,
                learning_style=request.learning_style,
                category=content.overview.category or None,
                difficulty=content.overview.difficulty or request.level,
                estimated_study_time=content.overview.estimated_study_time or None,
                description=content.overview.definition or None,
            )

            self._progress.record_pattern_learned(
                user.user_id,
                pattern_name=request.pattern,
                next_pattern=next_pattern,
            )

            elapsed = int((time.perf_counter() - start) * 1000)
            response = to_generate_response(chat_response, request, pattern_session, mode_id=resolved_mode)
            return response.model_copy(
                update={
                    "usage": response.usage.model_copy(update={"execution_time_ms": elapsed}),
                },
            )
        except Exception as exc:
            logger.error("DSA pattern generation failed: %s", exc)
            raise

    async def generate_stream(
        self,
        user: AuthenticatedUser,
        request: GeneratePatternRequest,
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
    ) -> PatternHistoryListResponse:
        rows = self._patterns.list_by_user(user.user_id, limit=limit, offset=offset, search=search)
        total = self._patterns.count_by_user(user.user_id)
        page = (offset // limit) + 1 if limit > 0 else 1
        items = []
        for row in rows:
            preview = None
            message_count = 0
            model_id = None
            session = self._sessions.get_by_id(row.session_id)
            if session is not None:
                model_id = session.model_id if isinstance(session.model_id, str) else None
                preview = (session.summary or "")[:180] or None
            if self._messages is not None:
                messages = self._messages.list_by_session(row.session_id, limit=200, offset=0)
                message_count = len(messages)
                if messages and not preview:
                    preview = (messages[-1].content or "")[:180] or None
            items.append(
                to_history_item(
                    row,
                    preview=preview,
                    message_count=message_count,
                    model_id=model_id,
                ),
            )
        return PatternHistoryListResponse(items=items, page=page, page_size=limit, total=total)

    def get_history_detail(self, user: AuthenticatedUser, session_id: UUID) -> SessionDetailResponse:
        """History detail by AI session id (same id returned from generate/follow-up)."""
        pattern_session = self._require_by_ai_session(user, session_id)
        detail = self._platform.get_session_detail(user, pattern_session.session_id)
        return to_session_detail(detail, pattern_session)

    def delete_history(self, user: AuthenticatedUser, session_id: UUID) -> None:
        pattern_session = self._require_by_ai_session(user, session_id)
        ai_session_id = pattern_session.session_id
        self._patterns.delete(pattern_session.id)
        self._platform.delete_session(user, ai_session_id)

    def get_progress(self, user: AuthenticatedUser) -> ProgressResponse:
        progress = self._progress.get_or_create(user.user_id)
        mastery = [
            MasteryItem(
                pattern_name=m.pattern_name,
                status=m.status,
                sessions_count=m.sessions_count,
                practice_completed=m.practice_completed,
                quiz_attempts=m.quiz_attempts,
                best_quiz_score=m.best_quiz_score,
                mastery_pct=m.mastery_pct,
                last_studied_at=m.last_studied_at,
            )
            for m in self._progress.list_mastery(user.user_id)
        ]
        return ProgressResponse(
            patterns_learned=progress.patterns_learned,
            patterns_mastered=progress.patterns_mastered,
            practice_completed=progress.practice_completed,
            quizzes_completed=progress.quizzes_completed,
            average_quiz_score=progress.average_quiz_score,
            current_streak=progress.current_streak,
            longest_streak=progress.longest_streak,
            learning_time_minutes=progress.learning_time_minutes,
            recommended_next_pattern=progress.recommended_next_pattern,
            weak_patterns=list(progress.weak_patterns or []),
            strong_patterns=list(progress.strong_patterns or []),
            patterns=list(progress.patterns or []),
            mastery=mastery,
            updated_at=progress.updated_at,
        )

    def get_dashboard(self, user: AuthenticatedUser) -> DashboardResponse:
        progress = self.get_progress(user)
        recent = self.list_history(user, limit=5, offset=0)
        active = next((item for item in recent.items if item.completion_pct < 100), None)
        return DashboardResponse(progress=progress, recent_sessions=recent.items, active_session=active)

    def update_progress(self, user: AuthenticatedUser, request: UpdateProgressRequest) -> ProgressResponse:
        pattern_session = self._require_pattern_owner(user, request.pattern_session_id)
        self._patterns.update_progress(
            pattern_session.id,
            practice_completed_delta=request.practice_completed_delta,
            study_minutes_delta=request.study_minutes_delta,
            quiz_score=request.quiz_score,
            completion_pct=request.completion_pct,
            mark_completed=request.mark_completed,
            mark_mastered=request.mark_mastered,
        )
        self._progress.apply_deltas(
            user.user_id,
            pattern_name=pattern_session.pattern_name,
            practice_completed_delta=request.practice_completed_delta,
            quizzes_completed_delta=request.quizzes_completed_delta,
            quiz_score=request.quiz_score,
            study_minutes_delta=request.study_minutes_delta,
            mark_mastered=request.mark_mastered,
        )
        return self.get_progress(user)

    def add_bookmark(self, user: AuthenticatedUser, request: BookmarkRequest) -> BookmarkResponse:
        pattern_session = self._require_pattern_owner(user, request.pattern_session_id)
        bookmark = self._patterns.add_bookmark(
            user_id=user.user_id,
            pattern_session_id=pattern_session.id,
            item_type=request.item_type,
            item_id=request.item_id,
            title=request.title,
        )
        return BookmarkResponse(
            id=bookmark.id,
            pattern_session_id=bookmark.pattern_session_id,
            item_type=bookmark.item_type,
            item_id=bookmark.item_id,
            title=bookmark.title,
            created_at=bookmark.created_at,
        )

    def list_examples(self) -> list[PatternExampleResponse]:
        return catalog_examples()

    def export(self, user: AuthenticatedUser, request: ExportRequest, *, fmt: str) -> ExportResponse:
        pattern_session = self._require_pattern_owner(user, request.pattern_session_id)
        content = pattern_to_content(pattern_session)
        safe_title = (
            "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in pattern_session.pattern_name)[:60]
            or "dsa_pattern"
        )

        if fmt == "json":
            payload = content.model_dump()
            if request.include:
                filtered: dict = {}
                mapping = {
                    "overview": "overview",
                    "mental_model": "mental_model",
                    "recognition": "recognition",
                    "visualization": "visualization",
                    "templates": "templates",
                    "examples": None,
                    "interview_tips": "interview_tips",
                    "practice": "practice",
                    "quiz": "quiz",
                    "comparison": "pattern_comparison",
                }
                for key in request.include:
                    if key == "examples":
                        filtered["easy_example"] = payload.get("easy_example")
                        filtered["medium_example"] = payload.get("medium_example")
                        filtered["hard_example"] = payload.get("hard_example")
                        continue
                    target = mapping.get(key, key)
                    if target and target in payload:
                        filtered[target] = payload[target]
                if "overview" not in filtered and payload.get("overview"):
                    filtered["overview"] = payload["overview"]
                payload = filtered
            body = json.dumps(payload, indent=2, default=str)
            return ExportResponse(
                pattern_session_id=pattern_session.id,
                format="json",
                filename=f"{safe_title}.json",
                content=body,
                content_type="application/json",
            )

        markdown = content_to_markdown(content, include=request.include)
        if fmt == "markdown":
            return ExportResponse(
                pattern_session_id=pattern_session.id,
                format="markdown",
                filename=f"{safe_title}.md",
                content=markdown,
                content_type="text/markdown",
            )

        pdf_bytes = markdown_to_simple_pdf(markdown, title=pattern_session.title)
        return ExportResponse(
            pattern_session_id=pattern_session.id,
            format="pdf",
            filename=f"{safe_title}.pdf",
            content=pdf_bytes.decode("latin-1"),
            content_type="application/pdf",
        )

    def _require_pattern_owner(self, user: AuthenticatedUser, pattern_session_id: UUID):
        row = self._patterns.get_by_id(pattern_session_id)
        if row is None:
            raise RecordNotFoundError(f"Pattern session '{pattern_session_id}' not found.")
        if not can_access_session(user, row.user_id):
            raise ForbiddenError("You do not have access to this pattern session.")
        return row

    def list_versions(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
    ) -> list[VersionHistoryItem]:
        if self._messages is None:
            raise RuntimeError("Message repository is not configured.")
        pattern_session = self._require_by_ai_session(user, session_id)
        records = build_assistant_version_history(
            self._messages.list_all_by_session(pattern_session.session_id),
        )
        return [VersionHistoryItem.model_validate(record.__dict__) for record in records]

    def _require_by_ai_session(self, user: AuthenticatedUser, session_id: UUID):
        session = self._sessions.get_by_id(session_id)
        if session is None or session.feature != AIFeature.DSA_PATTERN:
            # Also allow lookup by pattern_session.id for convenience.
            row = self._patterns.get_by_id(session_id)
            if row is not None:
                if not can_access_session(user, row.user_id):
                    raise ForbiddenError("You do not have access to this pattern session.")
                return row
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")
        row = self._patterns.get_by_session_id(session_id)
        if row is None:
            raise RecordNotFoundError(f"Pattern session for '{session_id}' not found.")
        return row
