"""AI platform use-case service."""

from __future__ import annotations

import time
from uuid import UUID

from app.agents.shared.memory.summarizer import ConversationSummarizer
from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.clients.openrouter import OpenRouterClient
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import AIFeature
from app.repositories.ai_session_repository import AISessionRepository
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
from app.services.followup.followup_service import FollowUpService
from app.services.history.history_manager import HistoryManager
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.models.model_registry import ModelRegistry, get_model_registry
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)


class AIPlatformService:
    """Generic AI platform service for all products."""

    def __init__(
        self,
        *,
        orchestrator: AIPlatformOrchestrator,
        history_manager: HistoryManager,
        session_repo: AISessionRepository,
        followup_service: FollowUpService | None = None,
        memory_service: ConversationMemoryService | None = None,
        summarizer: ConversationSummarizer | None = None,
        llm_client: OpenRouterClient | None = None,
        model_registry: ModelRegistry | None = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._history = history_manager
        self._sessions = session_repo
        self._followup = followup_service
        self._memory = memory_service
        self._summarizer = summarizer or ConversationSummarizer()
        self._llm = llm_client or OpenRouterClient()
        self._models = model_registry or get_model_registry()

    @property
    def model_registry(self) -> ModelRegistry:
        return self._models

    async def chat(self, user: AuthenticatedUser, request: ChatRequest) -> ChatResponse:
        session = None
        if request.session_id is not None:
            session = self._sessions.get_by_id(request.session_id)
            if session is None:
                raise RecordNotFoundError(f"Session '{request.session_id}' not found.")
            if not can_access_session(user, session.user_id):
                raise ForbiddenError("You do not have access to this session.")

        resolved_model = self._models.resolve_model_id(
            requested=request.model,
            session_model_id=session.model_id if session is not None else None,
        )
        request = request.model_copy(update={"model": resolved_model})
        return await self._orchestrator.execute(user_id=user.user_id, request=request)

    def list_history(
        self,
        user: AuthenticatedUser,
        *,
        feature: AIFeature | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> HistoryListResponse:
        return self._history.list_history(
            user,
            feature=feature,
            search=search,
            limit=limit,
            offset=offset,
        )

    def get_session_detail(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> SessionDetailResponse:
        return self._history.get_session_detail(
            user,
            session_id,
            limit=limit,
            offset=offset,
        )

    def delete_session(self, user: AuthenticatedUser, session_id: UUID) -> None:
        self._history.delete_session(user, session_id)

    async def follow_up(self, user: AuthenticatedUser, request: FollowUpRequest) -> FollowUpResponse:
        if self._followup is None:
            raise RuntimeError("Follow-up service is not configured.")
        session = self._sessions.get_by_id(request.session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{request.session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")

        resolved_model = self._models.resolve_model_id(
            requested=request.model,
            session_model_id=session.model_id,
        )
        resolved_mode = request.mode_id or session.mode_id
        request = request.model_copy(
            update={"model": resolved_model, "mode_id": resolved_mode},
        )
        return await self._followup.handle_follow_up(user, request)

    async def summarize_session(
        self,
        user: AuthenticatedUser,
        session_id: UUID,
        *,
        model: str | None = None,
    ) -> SummarizeResponse:
        start = time.perf_counter()
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")
        if self._memory is None:
            raise RuntimeError("Memory service is not configured.")

        memory = self._memory.load(session_id)
        messages = (memory or {}).get("recent_messages") or []
        existing_summary = (memory or {}).get("summary")

        summary, usage = await self._summarizer.summarize(
            session_id=session_id,
            messages=messages,
            existing_summary=existing_summary,
            model=model,
        )

        self._memory.save(
            session_id=session_id,
            user_id=session.user_id,
            summary=summary,
            context=(memory or {}).get("context"),
            recent_messages=messages,
            previous_responses=(memory or {}).get("long_term"),
            follow_up_questions=(memory or {}).get("follow_up_questions"),
        )

        elapsed = int((time.perf_counter() - start) * 1000)
        logger.info("session_summarized", extra={"session_id": str(session_id), "latency_ms": elapsed})

        return SummarizeResponse(
            session_id=session_id,
            summary=summary,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            latency_ms=usage.get("latency_ms", 0),
            execution_time_ms=elapsed,
        )

    def clear_memory(self, user: AuthenticatedUser, session_id: UUID) -> None:
        session = self._sessions.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")
        if self._memory is None:
            raise RuntimeError("Memory service is not configured.")
        self._memory.delete(session_id)

    def list_models(self) -> ModelsResponse:
        return self._models.list_models()
