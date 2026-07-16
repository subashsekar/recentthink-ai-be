"""LangGraph workflow node implementations."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID
from uuid import UUID

from app.coaching.registry import get_mode_registry
from app.agents.shared.coder.module import CoderModule
from app.agents.shared.code_explainer.module import CodeExplainerModule
from app.agents.shared.evaluator.module import EvaluatorModule
from app.agents.shared.llm_response_normalizer import (
    feature_payload_missing_content,
    is_llm_response_empty,
    normalize_unified_llm_payload,
)
from app.agents.shared.planner.planner import Planner
from app.agents.shared.teacher.module import TeacherModule
from app.clients.openrouter import OpenRouterClient
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import TOP_LEVEL_SECTIONS, resolve_feature_max_tokens
from app.cache import CacheManager, get_cache_manager
from app.models.enums import AIFeature, AgentRunStatus, MessageRole, ModuleName, SessionStatus, WorkflowStatus
from app.prompts.builder import PromptBuilder
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import ChatRequest, ModuleResponse, PlannerOutput
from app.schemas.llm_response import UnifiedLLMResponse
from app.agents.shared.workflow.llm_invocation import OpenRouterInvocation, build_openrouter_invocation
from app.services.execution_trace import ExecutionTraceService
from app.services.json_validator import JSONValidator
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker
from app.utils.cost_calculator import CostCalculator
from app.utils.prompt_sanitizer import sanitize_user_input
from app.utils.section_tokens import (
    estimate_section_tokens,
    filter_payload_to_sections,
    merge_llm_payload,
    resolve_prior_payload,
)
from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger(__name__)

_MODULE_PROCESSORS: dict[ModuleName, tuple[Any, str]] = {}


def _get_processors(
    teacher: TeacherModule,
    coder: CoderModule,
    code_explainer: CodeExplainerModule,
    evaluator: EvaluatorModule,
) -> dict[ModuleName, tuple[Any, str]]:
    return {
        ModuleName.TEACHER: (teacher, "teacher"),
        ModuleName.CODER: (coder, "coder"),
        ModuleName.CODE_EXPLAINER: (code_explainer, "code_explainer"),
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
        code_explainer: CodeExplainerModule | None = None,
        evaluator: EvaluatorModule | None = None,
        llm_client: OpenRouterClient | None = None,
        prompt_loader: PromptLoader | None = None,
        prompt_builder: PromptBuilder | None = None,
        json_validator: JSONValidator | None = None,
        cost_calculator: CostCalculator | None = None,
        session_repo: AISessionRepository | None = None,
        message_repo: AIMessageRepository | None = None,
        execution_trace: ExecutionTraceService | None = None,
        memory_service: ConversationMemoryService | None = None,
        usage_tracker: UsageTracker | None = None,
        cache_manager: CacheManager | None = None,
    ) -> None:
        self._planner = planner or Planner()
        self._teacher = teacher or TeacherModule()
        self._coder = coder or CoderModule()
        self._code_explainer = code_explainer or CodeExplainerModule()
        self._evaluator = evaluator or EvaluatorModule()
        self._llm = llm_client or OpenRouterClient()
        self._prompts = prompt_loader or PromptLoader()
        self._prompt_builder = prompt_builder or PromptBuilder(prompt_loader=self._prompts)
        self._validator = json_validator or JSONValidator()
        self._cost = cost_calculator or CostCalculator()
        self._sessions = session_repo
        self._messages = message_repo
        self._trace = execution_trace
        self._memory = memory_service
        self._usage = usage_tracker
        self._cache = cache_manager or get_cache_manager()
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
                max_tokens=state.get("max_tokens"),
                requested_sections=state.get("requested_sections"),
            )
            planner_output = self._planner.plan(request, mode_id=state.get("mode_id"))
            session = self._resolve_session(
                user_id=UUID(state["user_id"]),
                request=request,
                planner_output=planner_output,
            )
            modules_to_run = [m.value for m in planner_output.modules]
            requested = state.get("requested_sections")
            if requested:
                requested_top = [s for s in requested if s in TOP_LEVEL_SECTIONS]
                if requested_top:
                    modules_to_run = [m for m in modules_to_run if m in requested_top]
                elif ModuleName.TEACHER.value in modules_to_run:
                    # Nested-only regeneration still flows through teacher formatting.
                    modules_to_run = [ModuleName.TEACHER.value]
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
                "modules_to_run": modules_to_run,
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
        mode_registry = get_mode_registry()
        mode_cfg = mode_registry.resolve(state.get("mode_id"))
        requested_sections = state.get("requested_sections")
        built = self._prompt_builder.build(
            planner=planner,
            message=state.get("message", ""),
            context=state.get("context") if isinstance(state.get("context"), dict) else None,
            memory_context=state.get("memory_context") if isinstance(state.get("memory_context"), dict) else None,
            title=state.get("title"),
            mode_id=state.get("mode_id"),
            requested_sections=requested_sections,
        )
        system_prompt = built.system_prompt
        user_prompt = built.user_prompt
        llm_calls = 0
        max_json_retries = self._ai_settings.json_validation_max_retries
        response = None
        last_validation_error: str | None = None
        shared_settings = get_settings()
        model_name = state.get("model") or shared_settings.openrouter_model
        prompt_version = self._ai_settings.prompt_default_version
        max_tokens = resolve_feature_max_tokens(
            planner.feature.value,
            override=state.get("max_tokens"),
            requested_sections=requested_sections,
            limits=feature_max_tokens_map(self._ai_settings),
        )
        cache_key = self._cache.build_key(
            feature=planner.feature.value,
            model=str(model_name),
            prompt_version=prompt_version,
            context=state.get("context") if isinstance(state.get("context"), dict) else None,
            metadata=planner.metadata if isinstance(planner.metadata, dict) else None,
            message=state.get("message", ""),
        )
        prior_payload = resolve_prior_payload(
            context=state.get("context") if isinstance(state.get("context"), dict) else None,
            memory_context=state.get("memory_context") if isinstance(state.get("memory_context"), dict) else None,
        )

        try:
            if cache_key is not None:
                cached = self._cache.get(cache_key)
                if isinstance(cached, dict) and cached:
                    elapsed = int((time.perf_counter() - start) * 1000)
                    working = cached
                    if requested_sections:
                        # Reuse full cache; emit only requested sections (no OpenRouter).
                        working = merge_llm_payload(
                            prior_payload or cached,
                            filter_payload_to_sections(cached, requested_sections),
                            requested_sections=requested_sections,
                        )
                    section_tokens = estimate_section_tokens(
                        filter_payload_to_sections(cached, requested_sections) if requested_sections else cached,
                        completion_tokens=0,
                        requested_sections=requested_sections,
                    )
                    self._complete_trace(
                        state,
                        trace_entry,
                        ModuleName.OPENROUTER,
                        AgentRunStatus.SUCCESS,
                        execution_time_ms=elapsed,
                        latency_ms=elapsed,
                        input_tokens=0,
                        output_tokens=0,
                        estimated_cost=0.0,
                        trace_metadata={
                            "model": model_name,
                            "provider": "cache",
                            "llm_calls": 0,
                            "cache_hit": True,
                            "cache_key": cache_key,
                            "requested_sections": requested_sections,
                            "max_tokens": max_tokens,
                        },
                    )
                    return {
                        "llm_raw": working,
                        "teacher_output": working.get("teacher"),
                        "coder_output": working.get("coder"),
                        "evaluator_output": working.get("evaluator"),
                        "latency_ms": elapsed,
                        "section_tokens": section_tokens,
                        "regenerated_sections": list(requested_sections) if requested_sections else None,
                        "token_usage": {
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "total_tokens": 0,
                            "model": model_name,
                            "provider": "cache",
                            "temperature": float(
                                state.get("temperature", mode_cfg.generation.temperature),
                            ),
                            "estimated_cost_usd": 0.0,
                            "estimated_cost_inr": 0.0,
                            "cache_hit": True,
                            "section_tokens": section_tokens,
                            "max_tokens": max_tokens,
                        },
                    }

            validated_payload: dict[str, Any] | None = None
            attempt_max_tokens = max_tokens
            for json_attempt in range(max_json_retries + 1):
                llm_calls += 1
                response = await self._llm.chat_completion(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=state.get("model"),
                    temperature=float(state.get("temperature", mode_cfg.generation.temperature)),
                    max_tokens=attempt_max_tokens,
                    top_p=mode_cfg.generation.top_p,
                    frequency_penalty=mode_cfg.generation.frequency_penalty,
                    presence_penalty=mode_cfg.generation.presence_penalty,
                )
                validation = self._validator.validate(response.content, UnifiedLLMResponse)
                if not validation.success or validation.data is None:
                    last_validation_error = validation.error
                    if response.truncated or not (response.content or "").rstrip().endswith("}"):
                        # Truncated JSON is the usual cause of empty DSA/course payloads.
                        attempt_max_tokens = min(16000, max(attempt_max_tokens + 2048, int(attempt_max_tokens * 1.75)))
                        last_validation_error = (
                            f"{last_validation_error or 'invalid JSON'} "
                            f"(likely truncated; retrying with max_tokens={attempt_max_tokens})"
                        )
                    logger.warning(
                        "llm_json_retry",
                        extra={
                            "attempt": json_attempt + 1,
                            "error": last_validation_error,
                            "finish_reason": response.finish_reason,
                            "max_tokens": attempt_max_tokens,
                            "content_chars": len(response.content or ""),
                        },
                    )
                    continue

                parsed = validation.data.model_dump()
                normalized = normalize_unified_llm_payload(
                    parsed,
                    planner_metadata=planner.metadata,
                    feature_name=planner.feature.value,
                )
                # When generating a subset, empty unrelated top-level fields are expected.
                if not requested_sections:
                    feature_empty = feature_payload_missing_content(planner.feature.value, normalized)
                    if (is_llm_response_empty(normalized) or feature_empty) and json_attempt < max_json_retries:
                        last_validation_error = (
                            "LLM returned empty feature content"
                            if feature_empty
                            else "LLM returned empty teacher/coder content"
                        )
                        logger.warning(
                            "llm_empty_response_retry",
                            extra={"attempt": json_attempt + 1, "feature": planner.feature.value},
                        )
                        continue

                    if feature_empty:
                        last_validation_error = "LLM returned empty feature content"
                        validated_payload = None
                        break

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

            generated_only = (
                filter_payload_to_sections(validated_payload, requested_sections)
                if requested_sections
                else validated_payload
            )
            merged_payload = merge_llm_payload(
                prior_payload,
                generated_only if requested_sections else validated_payload,
                requested_sections=requested_sections,
            )

            if cache_key is not None:
                # Always store the full merged payload so future hits can slice sections.
                self._cache.set(
                    cache_key,
                    merged_payload if requested_sections and prior_payload else validated_payload,
                    ttl=self._cache.ttl_for_feature(planner.feature.value),
                )

            cost = self._cost.estimate_request_cost(
                input_tokens=response.prompt_tokens,
                output_tokens=response.completion_tokens,
            )
            section_tokens = estimate_section_tokens(
                generated_only,
                completion_tokens=response.completion_tokens,
                requested_sections=requested_sections,
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
                trace_metadata={
                    "model": response.model,
                    "provider": response.provider,
                    "llm_calls": llm_calls,
                    "cache_hit": False,
                    "cache_key": cache_key,
                    "requested_sections": requested_sections,
                    "max_tokens": max_tokens,
                    "section_tokens": section_tokens,
                },
            )
            return {
                "llm_raw": merged_payload,
                "teacher_output": merged_payload.get("teacher"),
                "coder_output": merged_payload.get("coder"),
                "evaluator_output": merged_payload.get("evaluator"),
                "latency_ms": response.latency_ms,
                "section_tokens": section_tokens,
                "regenerated_sections": list(requested_sections) if requested_sections else None,
                "token_usage": {
                    "input_tokens": response.prompt_tokens,
                    "output_tokens": response.completion_tokens,
                    "total_tokens": response.total_tokens,
                    "model": response.model,
                    "provider": response.provider,
                    "temperature": response.temperature,
                    "estimated_cost_usd": cost.usd,
                    "estimated_cost_inr": cost.inr,
                    "cache_hit": False,
                    "section_tokens": section_tokens,
                    "max_tokens": max_tokens,
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

    def build_openrouter_invocation(self, state: AIWorkflowState) -> OpenRouterInvocation:
        return build_openrouter_invocation(
            state=state,
            prompt_builder=self._prompt_builder,
            cache_manager=self._cache,
        )

    async def try_openrouter_cache(
        self,
        state: AIWorkflowState,
        invocation: OpenRouterInvocation,
        *,
        trace_entry: dict[str, Any],
        start: float,
    ) -> dict[str, Any] | None:
        """Return openrouter_node-style payload on cache hit, else None."""
        cache_key = invocation.cache_key
        requested_sections = invocation.requested_sections
        prior_payload = invocation.prior_payload
        if cache_key is None:
            return None
        cached = self._cache.get(cache_key)
        if not isinstance(cached, dict) or not cached:
            return None

        elapsed = int((time.perf_counter() - start) * 1000)
        working = cached
        if requested_sections:
            working = merge_llm_payload(
                prior_payload or cached,
                filter_payload_to_sections(cached, requested_sections),
                requested_sections=requested_sections,
            )
        section_tokens = estimate_section_tokens(
            filter_payload_to_sections(cached, requested_sections) if requested_sections else cached,
            completion_tokens=0,
            requested_sections=requested_sections,
        )
        shared_settings = get_settings()
        model_name = invocation.model or shared_settings.openrouter_model
        self._complete_trace(
            state,
            trace_entry,
            ModuleName.OPENROUTER,
            AgentRunStatus.SUCCESS,
            execution_time_ms=elapsed,
            latency_ms=elapsed,
            input_tokens=0,
            output_tokens=0,
            estimated_cost=0.0,
            trace_metadata={
                "model": model_name,
                "provider": "cache",
                "llm_calls": 0,
                "cache_hit": True,
                "cache_key": cache_key,
                "requested_sections": requested_sections,
                "max_tokens": invocation.max_tokens,
            },
        )
        return {
            "llm_raw": working,
            "teacher_output": working.get("teacher"),
            "coder_output": working.get("coder"),
            "evaluator_output": working.get("evaluator"),
            "latency_ms": elapsed,
            "section_tokens": section_tokens,
            "regenerated_sections": list(requested_sections) if requested_sections else None,
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model": model_name,
                "provider": "cache",
                "temperature": invocation.temperature,
                "estimated_cost_usd": 0.0,
                "estimated_cost_inr": 0.0,
                "cache_hit": True,
                "section_tokens": section_tokens,
                "max_tokens": invocation.max_tokens,
            },
        }

    async def apply_llm_response(
        self,
        state: AIWorkflowState,
        *,
        invocation: OpenRouterInvocation,
        response: Any,
        trace_entry: dict[str, Any],
        start: float,
        llm_calls: int = 1,
    ) -> dict[str, Any]:
        """Validate, merge, cache, and trace a completed LLM response."""
        planner = invocation.planner
        requested_sections = invocation.requested_sections
        prior_payload = invocation.prior_payload
        cache_key = invocation.cache_key
        max_json_retries = self._ai_settings.json_validation_max_retries
        last_validation_error: str | None = None
        validated_payload: dict[str, Any] | None = None

        for json_attempt in range(max_json_retries + 1):
            validation = self._validator.validate(response.content, UnifiedLLMResponse)
            if not validation.success or validation.data is None:
                last_validation_error = validation.error
                logger.warning(
                    "llm_json_retry",
                    extra={"attempt": json_attempt + 1, "error": last_validation_error},
                )
                if json_attempt >= max_json_retries:
                    break
                response = await self._llm.chat_completion(
                    system_prompt=invocation.system_prompt,
                    user_prompt=invocation.user_prompt,
                    model=invocation.model,
                    temperature=invocation.temperature,
                    max_tokens=invocation.max_tokens,
                    top_p=invocation.top_p,
                    frequency_penalty=invocation.frequency_penalty,
                    presence_penalty=invocation.presence_penalty,
                )
                llm_calls += 1
                continue

            parsed = validation.data.model_dump()
            normalized = normalize_unified_llm_payload(
                parsed,
                planner_metadata=planner.metadata,
                feature_name=planner.feature.value,
            )
            if not requested_sections:
                feature_empty = feature_payload_missing_content(planner.feature.value, normalized)
                if (is_llm_response_empty(normalized) or feature_empty) and json_attempt < max_json_retries:
                    last_validation_error = (
                        "LLM returned empty feature content"
                        if feature_empty
                        else "LLM returned empty teacher/coder content"
                    )
                    logger.warning(
                        "llm_empty_response_retry",
                        extra={"attempt": json_attempt + 1, "feature": planner.feature.value},
                    )
                    response = await self._llm.chat_completion(
                        system_prompt=invocation.system_prompt,
                        user_prompt=invocation.user_prompt,
                        model=invocation.model,
                        temperature=invocation.temperature,
                        max_tokens=invocation.max_tokens,
                        top_p=invocation.top_p,
                        frequency_penalty=invocation.frequency_penalty,
                        presence_penalty=invocation.presence_penalty,
                    )
                    llm_calls += 1
                    continue

                if feature_empty:
                    last_validation_error = "LLM returned empty feature content"
                    validated_payload = None
                    break

            validated_payload = normalized
            break

        elapsed = int((time.perf_counter() - start) * 1000)
        if validated_payload is None:
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

        generated_only = (
            filter_payload_to_sections(validated_payload, requested_sections)
            if requested_sections
            else validated_payload
        )
        merged_payload = merge_llm_payload(
            prior_payload,
            generated_only if requested_sections else validated_payload,
            requested_sections=requested_sections,
        )

        if cache_key is not None:
            self._cache.set(
                cache_key,
                merged_payload if requested_sections and prior_payload else validated_payload,
                ttl=self._cache.ttl_for_feature(planner.feature.value),
            )

        cost = self._cost.estimate_request_cost(
            input_tokens=response.prompt_tokens,
            output_tokens=response.completion_tokens,
        )
        section_tokens = estimate_section_tokens(
            generated_only,
            completion_tokens=response.completion_tokens,
            requested_sections=requested_sections,
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
            trace_metadata={
                "model": response.model,
                "provider": response.provider,
                "llm_calls": llm_calls,
                "cache_hit": False,
                "cache_key": cache_key,
                "requested_sections": requested_sections,
                "max_tokens": invocation.max_tokens,
                "section_tokens": section_tokens,
            },
        )
        return {
            "llm_raw": merged_payload,
            "teacher_output": merged_payload.get("teacher"),
            "coder_output": merged_payload.get("coder"),
            "evaluator_output": merged_payload.get("evaluator"),
            "latency_ms": response.latency_ms,
            "section_tokens": section_tokens,
            "regenerated_sections": list(requested_sections) if requested_sections else None,
            "token_usage": {
                "input_tokens": response.prompt_tokens,
                "output_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
                "model": response.model,
                "provider": response.provider,
                "temperature": response.temperature,
                "estimated_cost_usd": cost.usd,
                "estimated_cost_inr": cost.inr,
                "cache_hit": False,
                "section_tokens": section_tokens,
                "max_tokens": invocation.max_tokens,
            },
        }

    async def run_post_llm_pipeline(
        self,
        state: AIWorkflowState,
        *,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        assistant_ids_before: set[UUID] | None = None,
    ) -> dict[str, Any]:
        """Run teacher → coder → code_explainer → evaluator → persist sequentially."""
        merged: dict[str, Any] = dict(state)
        for node_name in ("teacher", "coder", "code_explainer", "evaluator", "persist"):
            if cancel_check is not None and await cancel_check():
                self.rollback_stream_assistant_messages(
                    merged.get("session_id"),
                    assistant_ids_before or set(),
                )
                return {**merged, "cancelled": True}
            node_fn = getattr(self, f"{node_name}_node")
            result = await node_fn(merged)
            merged.update(result)
        return merged

    def snapshot_assistant_message_ids(self, session_id: str | None) -> set[UUID]:
        if self._messages is None or not session_id:
            return set()
        from app.models.enums import MessageRole

        messages = self._messages.list_by_session(UUID(session_id), limit=5000, offset=0)
        return {message.id for message in messages if message.role == MessageRole.ASSISTANT}

    def rollback_stream_assistant_messages(
        self,
        session_id: str | None,
        assistant_ids_before: set[UUID],
    ) -> None:
        if self._messages is None or not session_id:
            return
        from app.models.enums import MessageRole

        messages = self._messages.list_by_session(UUID(session_id), limit=5000, offset=0)
        for message in messages:
            if message.role == MessageRole.ASSISTANT and message.id not in assistant_ids_before:
                try:
                    self._messages.delete_message(message.id)
                except Exception as exc:
                    logger.warning(
                        "rollback_assistant_message_failed",
                        extra={"message_id": str(message.id), "error": str(exc)},
                    )

    async def teacher_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.TEACHER)

    async def coder_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.CODER)

    async def code_explainer_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.CODE_EXPLAINER)

    async def evaluator_node(self, state: AIWorkflowState) -> dict[str, Any]:
        return await self._run_module_node(state, ModuleName.EVALUATOR)

    async def persist_node(self, state: AIWorkflowState) -> dict[str, Any]:
        start = time.perf_counter()
        trace_entry = self._begin_trace(state, ModuleName.PERSIST)
        session_id = UUID(state["session_id"])
        user_id = UUID(state["user_id"])
        errors = list(state.get("errors", []))
        prior_status = state.get("status")
        if prior_status == WorkflowStatus.FAILED.value:
            final_status = WorkflowStatus.FAILED
        elif errors:
            final_status = WorkflowStatus.PARTIAL
        else:
            final_status = WorkflowStatus.COMPLETED

        try:
            module_outputs = state.get("module_responses") or []
            summary = module_outputs[0]["content"] if module_outputs else None
            if self._sessions is not None:
                session_status = (
                    SessionStatus.FAILED
                    if final_status == WorkflowStatus.FAILED
                    else SessionStatus.COMPLETED if not errors else SessionStatus.FAILED
                )
                self._sessions.update_session(
                    session_id,
                    status=session_status,
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
                    section_tokens=(
                        state.get("section_tokens")
                        or token_usage.get("section_tokens")
                        or None
                    ),
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
        processors = _get_processors(self._teacher, self._coder, self._code_explainer, self._evaluator)
        processor, key = processors[module_name]
        if module_name == ModuleName.CODE_EXPLAINER:
            # Code explainer derives from the full normalized LLM payload + current module outputs.
            payload = {
                "llm_raw": state.get("llm_raw") or {},
                "coder_output": state.get("coder_output") or {},
                "evaluator_output": state.get("evaluator_output") or {},
                "planner_output": state.get("planner_output") or {},
            }
        else:
            payload = state.get(f"{key}_output") or (state.get("llm_raw") or {}).get(key) or {}
            if module_name == ModuleName.TEACHER and isinstance(payload, dict):
                course = (state.get("llm_raw") or {}).get("course")
                if isinstance(course, dict) and course:
                    payload = {**payload, "course": course}
                dsa_pattern = (state.get("llm_raw") or {}).get("dsa_pattern")
                if isinstance(dsa_pattern, dict) and dsa_pattern:
                    payload = {**payload, "dsa_pattern": dsa_pattern}
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
