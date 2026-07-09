"""LangGraph workflow node implementations."""

from __future__ import annotations

import json
import time
from typing import Any
from uuid import UUID

from app.agents.shared.coaching_modes import build_mode_prompt_prefix
from app.agents.shared.coder.module import CoderModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.llm_response_normalizer import (
    is_llm_response_empty,
    normalize_unified_llm_payload,
)
from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.clients.openrouter import OpenRouterClient
from app.core.config import get_ai_settings
from app.models.enums import AIFeature, AgentRunStatus, MessageRole, ModuleName, SessionStatus, WorkflowStatus
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import ChatRequest, ModuleResponse, PlannerOutput
from app.schemas.llm_response import UnifiedLLMResponse
from app.schemas.workflow import AIWorkflowState
from app.services.execution_trace import ExecutionTraceService
from app.services.json_validator import JSONValidator
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker
from app.utils.cost_calculator import CostCalculator
from app.utils.prompt_sanitizer import sanitize_user_input
from shared.logging import get_logger

logger = get_logger(__name__)

_MODULE_PROCESSORS: dict[ModuleName, tuple[Any, str]] = {}


def _get_processors(
    teacher: TeacherModule,
    coder: CoderModule,
    evaluator: EvaluatorModule,
) -> dict[ModuleName, tuple[Any, str]]:
    return {
        ModuleName.TEACHER: (teacher, "teacher"),
        ModuleName.CODER: (coder, "coder"),
        ModuleName.EVALUATOR: (evaluator, "evaluator"),
    }


class WorkflowNodes:
    """Single-responsibility LangGraph node handlers."""

    def __init__(
        self,
        *,
        planner: Planner | None = None,
        teacher: TeacherModule | None = None,
        coder: CoderModule | None = None,
        evaluator: EvaluatorModule | None = None,
        llm_client: OpenRouterClient | None = None,
        prompt_loader: PromptLoader | None = None,
        json_validator: JSONValidator | None = None,
        cost_calculator: CostCalculator | None = None,
        session_repo: AISessionRepository | None = None,
        message_repo: AIMessageRepository | None = None,
        execution_trace: ExecutionTraceService | None = None,
        memory_service: ConversationMemoryService | None = None,
        usage_tracker: UsageTracker | None = None,
    ) -> None:
        self._planner = planner or Planner()
        self._teacher = teacher or TeacherModule()
        self._coder = coder or CoderModule()
        self._evaluator = evaluator or EvaluatorModule()
        self._llm = llm_client or OpenRouterClient()
        self._prompts = prompt_loader or PromptLoader()
        self._validator = json_validator or JSONValidator()
        self._cost = cost_calculator or CostCalculator()
        self._sessions = session_repo
        self._messages = message_repo
        self._trace = execution_trace
        self._memory = memory_service
        self._usage = usage_tracker
        self._ai_settings = get_ai_settings()

    async def planner_node(self, state: AIWorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        trace_entry = self._begin_trace(state, ModuleName.PLANNER)
        try:
            request = ChatRequest(
                feature=AIFeature(state.get("feature_name", "leetcode")),
                message=state.get("message", ""),
                session_id=UUID(state["session_id"]) if state.get("session_id") else None,
                title=state.get("title"),
                context=state.get("context"),
                model=state.get("model"),
                temperature=state.get("temperature", 0.2),
                max_tokens=state.get("max_tokens", 4096),
            )
            planner_output = self._planner.plan(request)
            session = self._resolve_session(
                user_id=UUID(state["user_id"]),
                request=request,
                planner_output=planner_output,
            )
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.PLANNER,
                AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
                trace_metadata=planner_output.model_dump(),
            )
            self._persist_user_message(session.id, state.get("message", ""))
            memory_context = self._load_memory(session.id)
            return {
                "session_id": str(session.id),
                "planner_output": planner_output.model_dump(),
                "modules_to_run": [m.value for m in planner_output.modules],
                "feature_name": planner_output.feature.value,
                "memory_context": memory_context,
                "status": WorkflowStatus.IN_PROGRESS.value,
                "session_status": SessionStatus.IN_PROGRESS.value,
            }
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.PLANNER,
                AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc),
            )
            return {
                "errors": [*state.get("errors", []), f"planner: {exc}"],
                "status": WorkflowStatus.FAILED.value,
            }

    async def openrouter_node(self, state: AIWorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        trace_entry = self._begin_trace(state, ModuleName.OPENROUTER)
        planner = PlannerOutput.model_validate(state.get("planner_output") or {})
        system_prompt = self._prompts.load(
            feature=planner.feature.value,
            module_name="single_llm",
        )
        mode_prefix = build_mode_prompt_prefix(state.get("mode_id"))
        if mode_prefix:
            system_prompt = f"{mode_prefix}{system_prompt}"
        user_prompt = self._build_user_prompt(state, planner)
        llm_calls = 0
        max_json_retries = self._ai_settings.json_validation_max_retries
        response = None
        last_validation_error: str | None = None

        try:
            validated_payload: dict[str, Any] | None = None
            for json_attempt in range(max_json_retries + 1):
                llm_calls += 1
                response = await self._llm.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=state.get("model"),
                    temperature=state.get("temperature", 0.2),
                    max_tokens=state.get("max_tokens", 4096),
                )
                validation = self._validator.validate(response.content, UnifiedLLMResponse)
                if not validation.success or validation.data is None:
                    last_validation_error = validation.error
                    logger.warning(
                        "llm_json_retry",
                        extra={"attempt": json_attempt + 1, "error": last_validation_error},
                    )
                    continue

                parsed = validation.data.model_dump()
                normalized = normalize_unified_llm_payload(
                    parsed,
                    planner_metadata=planner.metadata,
                )
                if is_llm_response_empty(normalized) and json_attempt < max_json_retries:
                    last_validation_error = "LLM returned empty teacher/coder content"
                    logger.warning(
                        "llm_empty_response_retry",
                        extra={"attempt": json_attempt + 1},
                    )
                    continue

                validated_payload = normalized
                break

            elapsed = int((time.perf_counter() - start) * 1000)
            if validated_payload is None or response is None:
                self._complete_trace(
                    state,
                    trace_entry,
                    ModuleName.OPENROUTER,
                    AgentRunStatus.FAILED,
                    execution_time_ms=elapsed,
                    latency_ms=response.latency_ms if response else 0,
                    error_message=last_validation_error or "JSON validation failed",
                )
                return {
                    "errors": [
                        *state.get("errors", []),
                        f"openrouter: {last_validation_error or 'invalid JSON'}",
                    ],
                    "status": WorkflowStatus.PARTIAL.value,
                }

            cost = self._cost.estimate_request_cost(
                input_tokens=response.prompt_tokens,
                output_tokens=response.completion_tokens,
            )
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.OPENROUTER,
                AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
                latency_ms=response.latency_ms,
                input_tokens=response.prompt_tokens,
                output_tokens=response.completion_tokens,
                estimated_cost=cost.usd,
                trace_metadata={"model": response.model, "provider": response.provider, "llm_calls": llm_calls},
            )
            return {
                "llm_raw": validated_payload,
                "teacher_output": validated_payload.get("teacher"),
                "coder_output": validated_payload.get("coder"),
                "evaluator_output": validated_payload.get("evaluator"),
                "latency_ms": response.latency_ms,
                "token_usage": {
                    "input_tokens": response.prompt_tokens,
                    "output_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                    "model": response.model,
                    "provider": response.provider,
                    "temperature": response.temperature,
                    "estimated_cost_usd": cost.usd,
                    "estimated_cost_inr": cost.inr,
                },
            }
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.OPENROUTER,
                AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc),
            )
            return {
                "errors": [*state.get("errors", []), f"openrouter: {exc}"],
                "status": WorkflowStatus.FAILED.value,
            }

    async def teacher_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.TEACHER)

    async def coder_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.CODER)

    async def evaluator_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.EVALUATOR)

    async def persist_node(self, state: AIWorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        trace_entry = self._begin_trace(state, ModuleName.PERSIST)
        session_id = UUID(state["session_id"])
        user_id = UUID(state["user_id"])
        errors = list(state.get("errors", []))
        final_status = WorkflowStatus.COMPLETED if not errors else WorkflowStatus.PARTIAL

        try:
            module_outputs = state.get("module_responses") or []
            summary = module_outputs[0]["content"] if module_outputs else None
            if self._sessions is not None:
                self._sessions.update_session(
                    session_id,
                    status=SessionStatus.COMPLETED if not errors else SessionStatus.FAILED,
                    summary=summary[:500] if summary else None,
                )

            token_usage = state.get("token_usage") or {}
            if self._usage is not None and token_usage:
                await self._usage.record_request(
                    user_id=user_id,
                    session_id=session_id,
                    feature=state.get("feature_name", "unknown"),
                    model=str(token_usage.get("model", "")),
                    provider=str(token_usage.get("provider", "")),
                    input_tokens=int(token_usage.get("input_tokens", 0)),
                    output_tokens=int(token_usage.get("output_tokens", 0)),
                    latency_ms=int(state.get("latency_ms", 0)),
                    execution_time_ms=int(state.get("execution_time_ms", 0)),
                    estimated_cost=float(token_usage.get("estimated_cost_usd", 0)),
                )

            self._update_memory(state)
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.PERSIST,
                AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
            )
            return {
                "status": final_status.value,
                "session_status": SessionStatus.COMPLETED.value,
                "execution_time_ms": int(state.get("execution_time_ms", 0)) + elapsed,
            }
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                ModuleName.PERSIST,
                AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc),
            )
            logger.error("persist_node_failed", extra={"error": str(exc)})
            return {
                "errors": [*errors, f"persist: {exc}"],
                "status": WorkflowStatus.PARTIAL.value,
            }

    async def _run_module_node(
        self,
        state: AIWorkflowState,
        module_name: ModuleName,
    ) -> dict[str, Any]:
        modules_to_run = state.get("modules_to_run") or []
        if module_name.value not in modules_to_run:
            return {}

        start = time.perf_counter()
        trace_entry = self._begin_trace(state, module_name)
        processors = _get_processors(self._teacher, self._coder, self._evaluator)
        processor, key = processors[module_name]
        payload = state.get(f"{key}_output") or (state.get("llm_raw") or {}).get(key) or {}
        session_id = UUID(state["session_id"])

        try:
            result: ModuleResponse = processor.process(
                session_id=session_id,
                payload=payload if isinstance(payload, dict) else {"content": payload},
                message_repo=self._messages,
            )
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                module_name,
                AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
            )
            existing = list(state.get("module_responses") or [])
            existing.append(result.model_dump())
            return {
                "module_responses": existing,
                f"{key}_output": result.structured or payload,
                "execution_time_ms": int(state.get("execution_time_ms", 0)) + elapsed,
            }
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self._complete_trace(
                state,
                trace_entry,
                module_name,
                AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc),
            )
            logger.error("%s_node_failed", module_name.value, extra={"error": str(exc)})
            return {
                "errors": [*state.get("errors", []), f"{module_name.value}: {exc}"],
                "execution_time_ms": int(state.get("execution_time_ms", 0)) + elapsed,
            }

    def _resolve_session(
        self,
        *,
        user_id: UUID,
        request: ChatRequest,
        planner_output: PlannerOutput,
    ) -> Any:
        if self._sessions is None:
            raise RuntimeError("Session repository is required.")
        if request.session_id is not None:
            session = self._sessions.get_by_id(request.session_id)
            if session is None:
                from shared.exceptions.repository import RecordNotFoundError

                raise RecordNotFoundError(f"Session '{request.session_id}' not found.")
            self._sessions.update_session(session.id, status=SessionStatus.IN_PROGRESS)
            return session
        return self._sessions.create_session(
            user_id=user_id,
            feature=planner_output.feature,
            title=request.title,
            status=SessionStatus.IN_PROGRESS,
            context_metadata=request.context,
        )

    def _persist_user_message(self, session_id: UUID, message: str) -> None:
        if self._messages is None:
            return
        self._messages.create_message(
            session_id=session_id,
            role=MessageRole.USER,
            content=sanitize_user_input(message),
        )

    def _load_memory(self, session_id: UUID) -> dict[str, Any]:
        if self._memory is None:
            return {}
        return self._memory.build_prompt_context(session_id) or {}

    def _update_memory(self, state: AIWorkflowState) -> None:
        if self._memory is None:
            return
        evaluator = state.get("evaluator_output") or {}
        follow_ups = None
        if isinstance(evaluator, dict):
            follow_ups = evaluator.get("follow_up_questions") or evaluator.get("interview_questions")
        module_outputs = state.get("module_responses") or []
        summary = module_outputs[0]["content"] if module_outputs else ""
        planner_output = state.get("planner_output")
        teacher_output = state.get("teacher_output")
        memory_context: dict[str, Any] = {}
        if planner_output:
            memory_context["planner_output"] = planner_output
        if teacher_output:
            memory_context["teacher_output"] = teacher_output
        if state.get("context"):
            memory_context["problem"] = state.get("context")
        memory_context["feature"] = state.get("feature_name")
        self._memory.append_response(
            session_id=UUID(state["session_id"]),
            user_id=UUID(state["user_id"]),
            response_summary=summary,
            follow_up_questions=follow_ups if isinstance(follow_ups, list) else None,
            context=memory_context,
            user_message=state.get("message", ""),
        )

    def _begin_trace(self, state: AIWorkflowState, module_name: ModuleName) -> dict[str, Any]:
        entry = {
            "node_name": module_name.value,
            "status": AgentRunStatus.SUCCESS.value,
            "started_at": time.time(),
        }
        trace = list(state.get("trace") or [])
        trace.append(entry)
        return entry

    def _complete_trace(
        self,
        state: AIWorkflowState,
        trace_entry: dict[str, Any],
        module_name: ModuleName,
        status: AgentRunStatus,
        *,
        execution_time_ms: int = 0,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        estimated_cost: float = 0.0,
        error_message: str | None = None,
        trace_metadata: dict | None = None,
    ) -> None:
        trace_entry.update(
            {
                "status": status.value,
                "execution_time_ms": execution_time_ms,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "error_message": error_message,
                "completed_at": time.time(),
            },
        )
        session_id = state.get("session_id")
        workflow_id = state.get("workflow_id")
        if self._trace is not None and session_id:
            self._trace.record(
                session_id=UUID(session_id),
                module_name=module_name,
                status=status,
                execution_time_ms=execution_time_ms,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                token_usage=input_tokens + output_tokens,
                error_message=error_message,
                trace_metadata={
                    **(trace_metadata or {}),
                    "workflow_id": workflow_id,
                    "estimated_cost": estimated_cost,
                },
            )

    @staticmethod
    def _build_user_prompt(state: AIWorkflowState, planner: PlannerOutput) -> str:
        sections = [
            f"Feature: {planner.feature.value}",
            f"Classification: {planner.metadata.get('classification', 'general')}",
            f"Modules: {', '.join(module.value for module in planner.modules)}",
        ]
        metadata = planner.metadata or {}
        if planner.feature.value == "leetcode":
            context = state.get("context") or {}
            title = context.get("title") or state.get("title") or metadata.get("problem_slug") or "Unknown"
            problem_lines = [
                f"Title: {title}",
                f"Difficulty: {metadata.get('difficulty') or context.get('difficulty') or 'Unknown'}",
                f"Category: {metadata.get('problem_category', 'General')}",
                f"Patterns: {', '.join(metadata.get('patterns') or context.get('topics') or [])}",
            ]
            objectives = metadata.get("learning_objectives") or []
            if objectives:
                problem_lines.append("Learning objectives:")
                problem_lines.extend(f"- {item}" for item in objectives)
            plan = metadata.get("execution_plan") or []
            if plan:
                problem_lines.append("Execution plan:")
                problem_lines.extend(f"{index}. {step}" for index, step in enumerate(plan, start=1))
            sections.append("Problem metadata:\n" + "\n".join(problem_lines))
        context = state.get("context")
        if context:
            sections.append(f"Context:\n{json.dumps(context, indent=2, default=str)}")
        memory_context = state.get("memory_context")
        if memory_context:
            if memory_context.get("summary"):
                sections.append(f"Conversation summary:\n{memory_context['summary']}")
            if memory_context.get("planner_output"):
                sections.append(
                    f"Prior planner output:\n{json.dumps(memory_context['planner_output'], indent=2, default=str)}",
                )
            if memory_context.get("teacher_output"):
                sections.append(
                    f"Prior teacher output:\n{json.dumps(memory_context['teacher_output'], indent=2, default=str)}",
                )
            if memory_context.get("recent_messages"):
                sections.append(
                    f"Recent messages:\n{json.dumps(memory_context['recent_messages'], indent=2, default=str)}",
                )
            remaining = {
                k: v
                for k, v in memory_context.items()
                if k not in {"summary", "planner_output", "teacher_output", "recent_messages", "context"}
            }
            if remaining:
                sections.append(f"Memory:\n{json.dumps(remaining, indent=2, default=str)}")
        sections.append(f"User request:\n{state.get('message', '')}")
        return "\n\n".join(sections)
