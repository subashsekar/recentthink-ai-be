"""Follow-up request service with session-context validation."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from app.agents.shared.followup.context_validator import ContextValidator
from app.agents.shared.followup.engine import FollowUpEngine, FollowUpIntent
from app.agents.shared.teacher.module import TeacherModule
from app.agents.shared.teacher.parser import parse_teacher_payload
from app.clients.openrouter import OpenRouterClient
from app.coaching.prompt_loader import get_mode_prompt_loader
from app.coaching.registry import get_mode_registry
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import resolve_feature_max_tokens
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import MessageRole, ModuleName
from app.prompts.builder import PromptBuilder
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
        context_validator: ContextValidator | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._memory = memory_service
        self._llm = llm_client or OpenRouterClient()
        self._prompts = prompt_loader or PromptLoader()
        self._followup = followup_engine or FollowUpEngine()
        self._teacher = teacher or TeacherModule()
        self._usage = usage_tracker
        self._validator = context_validator or ContextValidator()
        self._prompt_builder = prompt_builder or PromptBuilder(prompt_loader=self._prompts)

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
        session_context = session.context_metadata if isinstance(session.context_metadata, dict) else {}
        feature = session.feature
        feature_name = feature.value if hasattr(feature, "value") else str(feature)
        prompt_version = get_ai_settings().prompt_default_version

        validation = self._validator.validate(
            question=question,
            feature=feature_name,
            session_context=session_context,
            memory_context=memory_context,
        )
        context_match = self._validator.is_accepted(validation)

        self._messages.create_message(
            session_id=request.session_id,
            role=MessageRole.USER,
            content=question,
            content_metadata={
                "follow_up_intent": intent.value if context_match else FollowUpIntent.OUT_OF_CONTEXT.value,
                "message_type": "follow_up",
                "generation_type": "follow_up",
                "prompt_version": prompt_version,
                "context_match": context_match,
                "context_confidence": validation.confidence,
                "context_reason": validation.reason,
                "retry_count": 0,
                "continue_state": None,
            },
        )

        if not context_match:
            return self._reject_out_of_context(
                user=user,
                session_id=request.session_id,
                feature_name=feature_name,
                question=question,
                validation_reason=validation.reason,
                rejection_message=validation.rejection_message
                or ContextValidator.build_rejection_message(feature_name),
                confidence=validation.confidence,
                prompt_version=prompt_version,
                start=start,
            )

        planner_metadata = memory_context.get("planner_output")
        if not isinstance(planner_metadata, dict):
            planner_metadata = None

        prompt_module = self._followup.resolve_prompt_module(intent)
        system_prompt = self._prompts.load(feature="teacher", module_name=prompt_module)
        teacher_system = self._prompts.load(feature="teacher", module_name="system")
        mode_cfg = get_mode_registry().resolve(request.mode_id or session.mode_id)
        mode_prompt = get_mode_prompt_loader().load(mode_cfg.followup_prompt or mode_cfg.metadata.id)
        instructions = self._followup.build_instructions(intent)
        session_outputs = self._load_session_outputs(request.session_id)

        built = self._prompt_builder.build_followup(
            feature=feature_name,
            question=question,
            intent=intent.value,
            instructions=instructions,
            session_context=session_context,
            memory_context=memory_context,
            session_outputs=session_outputs,
            mode_prompt=mode_prompt,
            teacher_system=teacher_system,
            followup_module_prompt=system_prompt,
            requested_sections=request.requested_sections,
        )

        resolved_model = request.model or session.model_id
        response = None
        final_payload: dict[str, Any] = {}
        max_attempts = 2
        effective_temperature = (
            request.temperature if request.temperature != 0.2 else mode_cfg.generation.temperature
        )
        effective_max_tokens = resolve_feature_max_tokens(
            feature_name,
            override=request.max_tokens,
            requested_sections=request.requested_sections,
            limits=feature_max_tokens_map(get_ai_settings()),
        )

        for attempt in range(max_attempts):
            response = await self._llm.chat_completion(
                system_prompt=built.system_prompt,
                user_prompt=built.user_prompt,
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
        self._annotate_assistant_message(
            request.session_id,
            intent=intent.value,
            context_match=True,
            prompt_version=prompt_version,
            generation_type="follow_up",
            rejected=False,
        )

        elapsed = int((time.perf_counter() - start) * 1000)
        self._memory.append_response(
            session_id=request.session_id,
            user_id=user.user_id,
            response_summary=teacher_result.content,
            context=memory_context.get("context"),
            user_message=question,
            message_type="follow_up",
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
                feature=feature_name,
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
                "feature": feature_name,
                "intent": intent.value,
                "context_match": True,
                "accepted": True,
                "rejected": False,
                "context_confidence": validation.confidence,
                "context_reason": validation.reason,
                "latency_ms": response.latency_ms,
                "execution_time_ms": elapsed,
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
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
            context_match=True,
            rejected=False,
        )

    def _reject_out_of_context(
        self,
        *,
        user: AuthenticatedUser,
        session_id: UUID,
        feature_name: str,
        question: str,
        validation_reason: str,
        rejection_message: str,
        confidence: float,
        prompt_version: str,
        start: float,
    ) -> FollowUpResponse:
        teacher = ModuleResponse(
            module=ModuleName.TEACHER,
            content=rejection_message,
            structured={
                "rejected": True,
                "context_match": False,
                "explanation": rejection_message,
                "problem_summary": "Out of session context",
            },
            metadata={
                "rejected": True,
                "context_match": False,
                "message_type": "follow_up_rejection",
            },
        )
        self._messages.create_message(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=rejection_message,
            module_name=ModuleName.TEACHER,
            content_metadata={
                "structured": teacher.structured,
                "markdown": rejection_message,
                "follow_up_intent": FollowUpIntent.OUT_OF_CONTEXT.value,
                "message_type": "follow_up_rejection",
                "generation_type": "follow_up",
                "prompt_version": prompt_version,
                "context_match": False,
                "context_confidence": confidence,
                "context_reason": validation_reason,
                "retry_count": 0,
                "continue_state": None,
                "rejected": True,
            },
        )
        self._memory.append_response(
            session_id=session_id,
            user_id=user.user_id,
            response_summary=rejection_message,
            user_message=question,
            message_type="follow_up_rejection",
        )
        elapsed = int((time.perf_counter() - start) * 1000)
        logger.info(
            "followup_request",
            extra={
                "session_id": str(session_id),
                "feature": feature_name,
                "intent": FollowUpIntent.OUT_OF_CONTEXT.value,
                "context_match": False,
                "accepted": False,
                "rejected": True,
                "context_confidence": confidence,
                "context_reason": validation_reason,
                "execution_time_ms": elapsed,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        )
        return FollowUpResponse(
            session_id=session_id,
            intent=FollowUpIntent.OUT_OF_CONTEXT.value,
            teacher=teacher,
            model=None,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            latency_ms=0,
            execution_time_ms=elapsed,
            context_match=False,
            rejected=True,
        )

    def _annotate_assistant_message(
        self,
        session_id: UUID,
        *,
        intent: str,
        context_match: bool,
        prompt_version: str,
        generation_type: str,
        rejected: bool,
    ) -> None:
        messages = self._messages.list_by_session(session_id, limit=200, offset=0)
        for message in reversed(messages):
            if message.role != MessageRole.ASSISTANT:
                continue
            metadata = dict(message.content_metadata or {})
            if metadata.get("follow_up_intent") or metadata.get("generation_type") == "follow_up":
                # Already annotated (e.g. rejection path).
                if metadata.get("follow_up_intent") == FollowUpIntent.OUT_OF_CONTEXT.value:
                    return
            metadata.update(
                {
                    "follow_up_intent": intent,
                    "message_type": "follow_up",
                    "generation_type": generation_type,
                    "prompt_version": prompt_version,
                    "context_match": context_match,
                    "retry_count": int(metadata.get("retry_count") or 0),
                    "continue_state": metadata.get("continue_state"),
                    "rejected": rejected,
                }
            )
            self._messages.update_message(message.id, content_metadata=metadata)
            return

    def _load_session_outputs(self, session_id: UUID) -> dict[str, Any]:
        """Load latest module outputs from session messages (summaries only)."""
        outputs: dict[str, Any] = {}
        messages = self._messages.list_by_session(session_id, limit=100, offset=0)
        for message in reversed(messages):
            if message.role != MessageRole.ASSISTANT or message.module_name is None:
                continue
            key = message.module_name.value
            if key in outputs:
                continue
            metadata = message.content_metadata or {}
            structured = metadata.get("structured")
            if isinstance(structured, dict) and structured:
                outputs[key] = structured
            else:
                outputs[key] = message.content
            # Prefer nested curriculum payloads when present.
            if isinstance(structured, dict):
                if isinstance(structured.get("course"), dict):
                    outputs["course"] = structured["course"]
                if isinstance(structured.get("dsa_pattern"), dict):
                    outputs["dsa_pattern"] = structured["dsa_pattern"]
            if len(outputs) >= 8:
                break
        return outputs
