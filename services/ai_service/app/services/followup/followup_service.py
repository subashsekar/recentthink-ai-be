"""Follow-up request service."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from app.agents.shared.followup.engine import FollowUpEngine, FollowUpIntent
from app.agents.shared.teacher.module import TeacherModule
from app.clients.openrouter import OpenRouterClient
from app.dependencies.auth import AuthenticatedUser, can_access_session
from app.models.enums import MessageRole, ModuleName
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import FollowUpRequest, FollowUpResponse, ModuleResponse
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker
from app.utils.prompt_sanitizer import sanitize_user_input
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

        self._messages.create_message(
            session_id=request.session_id,
            role=MessageRole.USER,
            content=question,
            content_metadata={"follow_up_intent": intent.value},
        )

        prompt_module = self._followup.resolve_prompt_module(intent)
        system_prompt = self._prompts.load(feature="teacher", module_name=prompt_module)
        teacher_system = self._prompts.load(feature="teacher", module_name="system")
        instructions = self._followup.build_instructions(intent)

        user_prompt = self._build_followup_prompt(
            question=question,
            intent=intent,
            instructions=instructions,
            memory_context=memory_context,
        )

        response = await self._llm.chat_completion(
            system_prompt=f"{teacher_system}\n\n{system_prompt}",
            user_prompt=user_prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        teacher_payload = self._parse_teacher_response(response.content)
        teacher_result: ModuleResponse = self._teacher.process(
            session_id=request.session_id,
            payload=teacher_payload,
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
    def _build_followup_prompt(
        *,
        question: str,
        intent: FollowUpIntent,
        instructions: str,
        memory_context: dict[str, Any],
    ) -> str:
        sections = [
            f"Follow-up intent: {intent.value}",
            f"Instructions: {instructions}",
        ]
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
            'Respond with a JSON object containing teacher fields: '
            '"problem_summary", "thinking_process", "concepts", "approach", '
            '"common_mistakes", "analogy", "next_step". Do not reveal the full solution.',
        )
        return "\n\n".join(sections)

    @staticmethod
    def _parse_teacher_response(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "teacher" in parsed:
                return parsed["teacher"]
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"explanation": content}
