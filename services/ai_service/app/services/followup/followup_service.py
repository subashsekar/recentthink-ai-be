"""Follow-up request service."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from app.coaching.registry import get_mode_registry
from app.coaching.prompt_loader import get_mode_prompt_loader
from app.agents.shared.followup.engine import FollowUpEngine, FollowUpIntent
from app.agents.shared.teacher.module import TeacherModule
from app.agents.shared.teacher.parser import parse_teacher_payload
from app.clients.openrouter import OpenRouterClient
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import resolve_feature_max_tokens
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import AIFeature, MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import FollowUpRequest, FollowUpResponse, ModuleResponse
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker
from app.utils.prompt_sanitizer import sanitize_user_input
from app.utils.section_tokens import estimate_section_tokens
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger

logger = get_logger(__name__)


class FollowUpService:
    """Handle follow-up questions using existing session context."""

    def __init__(
        self,
        *,
        session_repo: AISessionRepository,
        message_repo: AIMessageRepository,
        memory_service: ConversationMemoryService,
        llm_client: OpenRouterClient | None = None,
        prompt_loader: PromptLoader | None = None,
        followup_engine: FollowUpEngine | None = None,
        teacher: TeacherModule | None = None,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._memory = memory_service
        self._llm = llm_client or OpenRouterClient()
        self._prompts = prompt_loader or PromptLoader()
        self._followup = followup_engine or FollowUpEngine()
        self._teacher = teacher or TeacherModule()
        self._usage = usage_tracker

    async def handle_follow_up(
        self,
        user: AuthenticatedUser,
        request: FollowUpRequest,
    ) -> FollowUpResponse:
        start = time.perf_counter()
        session = self._sessions.get_by_id(request.session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{request.session_id}' not found.")
        if not can_access_session(user, session.user_id):
            raise ForbiddenError("You do not have access to this session.")

        question = sanitize_user_input(request.question)
        intent = self._followup.classify(question)
        memory_context = self._memory.build_prompt_context(request.session_id)
        planner_metadata = memory_context.get("planner_output")
        if not isinstance(planner_metadata, dict):
            planner_metadata = None

        self._messages.create_message(
            session_id=request.session_id,
            role=MessageRole.USER,
            content=question,
            content_metadata={"follow_up_intent": intent.value},
        )

        prompt_module = self._followup.resolve_prompt_module(intent)
        system_prompt = self._prompts.load(feature="teacher", module_name=prompt_module)
        teacher_system = self._prompts.load(feature="teacher", module_name="system")
        mode_cfg = get_mode_registry().resolve(request.mode_id or session.mode_id)
        mode_prompt = get_mode_prompt_loader().load(mode_cfg.followup_prompt or mode_cfg.metadata.id)

        instructions = self._followup.build_instructions(intent)
        problem_context = self._resolve_problem_context(session.context_metadata, memory_context)

        user_prompt = self._build_followup_prompt(
            question=question,
            intent=intent,
            instructions=instructions,
            memory_context=memory_context,
            problem_context=problem_context,
        )

        resolved_model = request.model or session.model_id
        response = None
        final_payload: dict[str, Any] = {}
        max_attempts = 2
        effective_temperature = (
            request.temperature if request.temperature != 0.2 else mode_cfg.generation.temperature
        )
        feature_name = session.feature.value if hasattr(session.feature, "value") else str(session.feature)
        effective_max_tokens = resolve_feature_max_tokens(
            feature_name,
            override=request.max_tokens,
            requested_sections=request.requested_sections,
            limits=feature_max_tokens_map(get_ai_settings()),
        )
        if request.requested_sections:
            user_prompt = (
                user_prompt
                + "\n\nRequested sections (generate ONLY these):\n"
                + json.dumps({"sections": request.requested_sections}, indent=2)
            )
        for attempt in range(max_attempts):
            response = await self._llm.chat_completion(
                system_prompt="\n\n".join([part for part in (mode_prompt, teacher_system, system_prompt) if part]),
                user_prompt=user_prompt,
                model=resolved_model,
                temperature=effective_temperature,
                max_tokens=effective_max_tokens,
                top_p=mode_cfg.generation.top_p,
                frequency_penalty=mode_cfg.generation.frequency_penalty,
                presence_penalty=mode_cfg.generation.presence_penalty,
                json_mode=True,
            )
            final_payload = parse_teacher_payload(
                response.content,
                planner_metadata=planner_metadata,
            )
            preview = self._teacher.process(
                session_id=request.session_id,
                payload=final_payload,
                message_repo=None,
            )
            if (
                preview.content.strip()
                and preview.content != "No teacher output available."
                and len(preview.content) >= 40
            ):
                break
            logger.warning(
                "followup_empty_response_retry",
                extra={"session_id": str(request.session_id), "attempt": attempt + 1},
            )

        assert response is not None
        teacher_result = self._teacher.process(
            session_id=request.session_id,
            payload=final_payload,
            message_repo=self._messages,
        )

        elapsed = int((time.perf_counter() - start) * 1000)
        self._memory.append_response(
            session_id=request.session_id,
            user_id=user.user_id,
            response_summary=teacher_result.content,
            context=memory_context.get("context"),
            user_message=question,
        )

        if self._usage is not None:
            section_tokens = estimate_section_tokens(
                {"teacher": final_payload},
                completion_tokens=response.completion_tokens,
                requested_sections=request.requested_sections,
            )
            await self._usage.record_request(
                user_id=user.user_id,
                session_id=request.session_id,
                feature=session.feature.value,
                model=response.model,
                provider=response.provider,
                input_tokens=response.prompt_tokens,
                output_tokens=response.completion_tokens,
                latency_ms=response.latency_ms,
                execution_time_ms=elapsed,
                estimated_cost=0.0,
                request_count=1,
                section_tokens=section_tokens or None,
            )

        logger.info(
            "followup_request",
            extra={
                "session_id": str(request.session_id),
                "intent": intent.value,
                "latency_ms": response.latency_ms,
                "execution_time_ms": elapsed,
            },
        )

        return FollowUpResponse(
            session_id=request.session_id,
            intent=intent.value,
            teacher=teacher_result,
            model=response.model,
            input_tokens=response.prompt_tokens,
            output_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            latency_ms=response.latency_ms,
            execution_time_ms=elapsed,
        )

    @staticmethod
    def _resolve_problem_context(
        session_context: dict[str, Any] | None,
        memory_context: dict[str, Any],
    ) -> dict[str, Any]:
        if isinstance(session_context, dict) and session_context.get("title"):
            return session_context
        nested = memory_context.get("context")
        if isinstance(nested, dict):
            problem = nested.get("problem")
            if isinstance(problem, dict) and problem.get("title"):
                return problem
            if nested.get("title"):
                return nested
        return session_context or {}

    @staticmethod
    def _build_followup_prompt(
        *,
        question: str,
        intent: FollowUpIntent,
        instructions: str,
        memory_context: dict[str, Any],
        problem_context: dict[str, Any] | None = None,
    ) -> str:
        sections = [
            f"Follow-up intent: {intent.value}",
            f"Instructions: {instructions}",
        ]
        problem = problem_context or {}
        if problem:
            problem_lines = [
                f"Title: {problem.get('title', 'Unknown')}",
                f"Difficulty: {problem.get('difficulty', 'Unknown')}",
            ]
            if problem.get("description"):
                description = str(problem["description"])
                problem_lines.append(f"Description:\n{description[:4000]}")
            if problem.get("constraints"):
                problem_lines.append(
                    "Constraints:\n" + "\n".join(f"- {item}" for item in problem["constraints"]),
                )
            sections.append("Problem context:\n" + "\n".join(problem_lines))
        if memory_context.get("summary"):
            sections.append(f"Conversation summary:\n{memory_context['summary']}")
        if memory_context.get("planner_output"):
            sections.append(f"Planner context:\n{json.dumps(memory_context['planner_output'], indent=2)}")
        if memory_context.get("teacher_output"):
            sections.append(f"Previous teacher output:\n{json.dumps(memory_context['teacher_output'], indent=2)}")
        if memory_context.get("recent_messages"):
            sections.append(f"Recent messages:\n{json.dumps(memory_context['recent_messages'], indent=2)}")
        sections.append(f"User follow-up question:\n{question}")
        sections.append(
            "Respond with a JSON object containing teacher fields: "
            '"problem_summary", "thinking_process", "learning_objectives", "concepts", '
            '"approach", "common_mistakes", "analogy", "next_step", "explanation", "hints". '
            "The explanation field must directly answer the follow-up question.",
        )
        return "\n\n".join(sections)

