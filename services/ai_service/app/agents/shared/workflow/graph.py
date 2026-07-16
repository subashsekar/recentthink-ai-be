"""LangGraph AI workflow engine."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.shared.workflow.nodes import WorkflowNodes
from app.clients.openrouter import LLMResponse, OpenRouterClient
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import TOP_LEVEL_SECTIONS, resolve_feature_max_tokens
from app.models.enums import ModuleName, SessionStatus, WorkflowStatus
from app.schemas.ai import ChatRequest, ChatResponse, ModuleResponse, PlannerOutput
from app.schemas.workflow import AIWorkflowState
from app.utils.openrouter_stream import parse_stream_delta, parse_stream_metadata
from app.utils.prompt_sanitizer import sanitize_user_input
from app.services.chat.message_metadata import (
    compute_missing_sections,
    expected_sections_from_planner,
    is_truncated_finish_reason,
    resolve_message_status,
)
from app.services.chat.stream_cancel import StreamCancelledError
from shared.logging import get_logger

logger = get_logger(__name__)


class AIWorkflowEngine:
    """Reusable LangGraph workflow: Planner → OpenRouter → Teacher → Coder → Code Explainer → Evaluator → Persist."""

    def __init__(self, nodes: WorkflowNodes | None = None) -> None:
        self._nodes = nodes or WorkflowNodes()
        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph: StateGraph = StateGraph(AIWorkflowState)
        graph.add_node("planner", self._nodes.planner_node)
        graph.add_node("openrouter", self._nodes.openrouter_node)
        graph.add_node("teacher", self._nodes.teacher_node)
        graph.add_node("coder", self._nodes.coder_node)
        graph.add_node("code_explainer", self._nodes.code_explainer_node)
        graph.add_node("evaluator", self._nodes.evaluator_node)
        graph.add_node("persist", self._nodes.persist_node)

        graph.add_edge(START, "planner")
        graph.add_edge("planner", "openrouter")
        graph.add_edge("openrouter", "teacher")
        graph.add_edge("teacher", "coder")
        graph.add_edge("coder", "code_explainer")
        graph.add_edge("code_explainer", "evaluator")
        graph.add_edge("evaluator", "persist")
        graph.add_edge("persist", END)

        return graph.compile(checkpointer=self._checkpointer)

    async def execute(
        self,
        *,
        user_id: UUID,
        request: ChatRequest,
    ) -> ChatResponse:
        pipeline_start = time.perf_counter()
        workflow_id = str(uuid4())
        sanitized_message = sanitize_user_input(request.message)
        sanitized_request = request.model_copy(update={"message": sanitized_message})
        resolved_max_tokens = resolve_feature_max_tokens(
            sanitized_request.feature.value,
            override=sanitized_request.max_tokens,
            requested_sections=sanitized_request.requested_sections,
            limits=feature_max_tokens_map(get_ai_settings()),
        )

        initial: AIWorkflowState = {
            "workflow_id": workflow_id,
            "session_id": str(sanitized_request.session_id) if sanitized_request.session_id else "",
            "user_id": str(user_id),
            "feature_name": sanitized_request.feature.value,
            "problem": sanitized_request.context or {},
            "message": sanitized_message,
            "title": sanitized_request.title,
            "context": sanitized_request.context,
            "model": sanitized_request.model,
            "mode_id": sanitized_request.mode_id,
            "temperature": sanitized_request.temperature,
            "max_tokens": resolved_max_tokens,
            "requested_sections": sanitized_request.requested_sections,
            "regenerated_sections": None,
            "section_tokens": {},
            "memory_context": {},
            "planner_output": None,
            "llm_raw": None,
            "teacher_output": None,
            "coder_output": None,
            "code_explainer_output": None,
            "evaluator_output": None,
            "module_responses": [],
            "token_usage": {},
            "execution_time_ms": 0,
            "latency_ms": 0,
            "errors": [],
            "trace": [],
            "status": WorkflowStatus.PENDING.value,
            "modules_to_run": [],
            "session_status": SessionStatus.PENDING.value,
        }

        config = {"configurable": {"thread_id": workflow_id}}
        result: AIWorkflowState = await self._graph.ainvoke(initial, config=config)

        total_execution_ms = int((time.perf_counter() - pipeline_start) * 1000)
        token_usage = result.get("token_usage") or {}
        planner_output = PlannerOutput.model_validate(result.get("planner_output") or {})
        module_outputs = [
            ModuleResponse.model_validate(item) for item in (result.get("module_responses") or [])
        ]
        regenerated = result.get("regenerated_sections")
        module_outputs = _filter_modules_for_sections(module_outputs, regenerated)

        status_map = {
            WorkflowStatus.COMPLETED.value: SessionStatus.COMPLETED,
            # Partial module issues still return usable content for LeetCode-style features.
            WorkflowStatus.PARTIAL.value: SessionStatus.COMPLETED,
            WorkflowStatus.FAILED.value: SessionStatus.FAILED,
        }
        session_status = status_map.get(
            result.get("status", WorkflowStatus.COMPLETED.value),
            SessionStatus.COMPLETED,
        )

        section_tokens = result.get("section_tokens") or token_usage.get("section_tokens") or None

        logger.info(
            "workflow_completed",
            extra={
                "workflow_id": workflow_id,
                "session_id": result.get("session_id"),
                "status": result.get("status"),
                "errors": result.get("errors"),
                "total_tokens": token_usage.get("total_tokens", 0),
                "execution_time_ms": total_execution_ms,
                "max_tokens": resolved_max_tokens,
                "section_tokens": section_tokens,
                "regenerated_sections": regenerated,
            },
        )

        return ChatResponse(
            session_id=UUID(result["session_id"]),
            status=session_status,
            planner=planner_output,
            modules=module_outputs,
            model=str(token_usage.get("model")) if token_usage.get("model") else None,
            provider=str(token_usage.get("provider")) if token_usage.get("provider") else None,
            input_tokens=int(token_usage.get("input_tokens", 0)),
            output_tokens=int(token_usage.get("output_tokens", 0)),
            total_tokens=int(token_usage.get("total_tokens", 0)),
            latency_ms=int(result.get("latency_ms", 0)),
            execution_time_ms=total_execution_ms,
            estimated_cost=float(token_usage.get("estimated_cost_usd", 0)),
            section_tokens=section_tokens if isinstance(section_tokens, dict) else None,
            regenerated_sections=list(regenerated) if regenerated else None,
        )

    async def execute_stream(
        self,
        *,
        user_id: UUID,
        request: ChatRequest,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the workflow with token streaming from OpenRouter."""
        pipeline_start = time.perf_counter()
        workflow_id = str(uuid4())
        sanitized_message = sanitize_user_input(request.message)
        sanitized_request = request.model_copy(update={"message": sanitized_message})
        resolved_max_tokens = resolve_feature_max_tokens(
            sanitized_request.feature.value,
            override=sanitized_request.max_tokens,
            requested_sections=sanitized_request.requested_sections,
            limits=feature_max_tokens_map(get_ai_settings()),
        )

        initial: AIWorkflowState = {
            "workflow_id": workflow_id,
            "session_id": str(sanitized_request.session_id) if sanitized_request.session_id else "",
            "user_id": str(user_id),
            "feature_name": sanitized_request.feature.value,
            "problem": sanitized_request.context or {},
            "message": sanitized_message,
            "title": sanitized_request.title,
            "context": sanitized_request.context,
            "model": sanitized_request.model,
            "mode_id": sanitized_request.mode_id,
            "temperature": sanitized_request.temperature,
            "max_tokens": resolved_max_tokens,
            "requested_sections": sanitized_request.requested_sections,
            "regenerated_sections": None,
            "section_tokens": {},
            "memory_context": {},
            "planner_output": None,
            "llm_raw": None,
            "teacher_output": None,
            "coder_output": None,
            "code_explainer_output": None,
            "evaluator_output": None,
            "module_responses": [],
            "token_usage": {},
            "execution_time_ms": 0,
            "latency_ms": 0,
            "errors": [],
            "trace": [],
            "status": WorkflowStatus.PENDING.value,
            "modules_to_run": [],
            "session_status": SessionStatus.PENDING.value,
        }

        async def _cancelled() -> bool:
            return cancel_check is not None and await cancel_check()

        try:
            yield {"type": "status", "status": "thinking"}

            planner_result = await self._nodes.planner_node(initial)
            state: dict[str, Any] = {**initial, **planner_result}
            if planner_result.get("errors"):
                yield {"type": "error", "message": "; ".join(planner_result.get("errors", []))}
                yield {"type": "done"}
                return

            assistant_ids_before = self._nodes.snapshot_assistant_message_ids(state.get("session_id"))

            if await _cancelled():
                yield {"type": "error", "message": "Stream cancelled."}
                yield {"type": "done"}
                return

            yield {"type": "status", "status": "preparing"}
            invocation = self._nodes.build_openrouter_invocation(state)
            start = time.perf_counter()
            trace_entry = self._nodes._begin_trace(state, ModuleName.OPENROUTER)

            cached = await self._nodes.try_openrouter_cache(
                state,
                invocation,
                trace_entry=trace_entry,
                start=start,
            )
            if cached is not None:
                state.update(cached)
                if await _cancelled():
                    self._nodes.rollback_stream_assistant_messages(
                        state.get("session_id"),
                        assistant_ids_before,
                    )
                    yield {"type": "error", "message": "Stream cancelled."}
                    yield {"type": "done"}
                    return
                yield {"type": "status", "status": "generating"}
                yield {"type": "status", "status": "explaining"}
                yield {"type": "status", "status": "evaluating"}
                final_state = await self._nodes.run_post_llm_pipeline(
                    state,
                    cancel_check=cancel_check,
                    assistant_ids_before=assistant_ids_before,
                )
                if final_state.get("cancelled"):
                    yield {"type": "error", "message": "Stream cancelled."}
                    yield {"type": "done"}
                    return
                response = self._build_chat_response(final_state, pipeline_start, resolved_max_tokens)
                stream_meta = self._build_stream_metadata(
                    final_state,
                    response,
                    finish_reason=None,
                    cache_hit=True,
                    action="stream",
                )
                yield {"type": "complete", "response": response.model_dump(mode="json"), "stream_meta": stream_meta}
                yield {"type": "done"}
                return

            yield {"type": "status", "status": "generating"}
            llm_client = self._nodes._llm
            content_parts: list[str] = []
            stream_model = invocation.model
            stream_provider = OpenRouterClient.parse_provider(stream_model or "")
            usage_meta: dict[str, Any] = {}
            finish_reason: str | None = None
            stream_start = time.perf_counter()

            try:
                async for chunk in llm_client.stream_completion(
                    system_prompt=invocation.system_prompt,
                    user_prompt=invocation.user_prompt,
                    model=invocation.model,
                    temperature=invocation.temperature,
                    max_tokens=invocation.max_tokens,
                    cancel_check=cancel_check,
                ):
                    meta = parse_stream_metadata(chunk)
                    if meta.get("model"):
                        stream_model = meta["model"]
                    if meta.get("usage"):
                        usage_meta = meta["usage"]
                    if meta.get("finish_reason"):
                        finish_reason = meta["finish_reason"]
                    delta = parse_stream_delta(chunk)
                    if delta:
                        content_parts.append(delta)
                        yield {"type": "token", "delta": delta}
            except StreamCancelledError:
                self._nodes.rollback_stream_assistant_messages(
                    state.get("session_id"),
                    assistant_ids_before,
                )
                yield {"type": "error", "message": "Stream cancelled."}
                yield {"type": "done"}
                return

            if await _cancelled():
                self._nodes.rollback_stream_assistant_messages(
                    state.get("session_id"),
                    assistant_ids_before,
                )
                yield {"type": "error", "message": "Stream cancelled."}
                yield {"type": "done"}
                return

            full_content = "".join(content_parts)
            latency_ms = int((time.perf_counter() - stream_start) * 1000)
            prompt_tokens = int(usage_meta.get("prompt_tokens", 0)) if usage_meta else 0
            completion_tokens = int(usage_meta.get("completion_tokens", 0)) if usage_meta else max(
                len(full_content) // 4,
                1,
            )
            if stream_model:
                stream_provider = OpenRouterClient.parse_provider(stream_model)

            if is_truncated_finish_reason(finish_reason) or completion_tokens >= int(
                invocation.max_tokens * 0.95,
            ):
                finish_reason = finish_reason or "length"

            llm_response = LLMResponse(
                content=full_content,
                model=stream_model or "unknown",
                provider=stream_provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                estimated_cost=llm_client.estimate_cost(
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                ),
                temperature=invocation.temperature,
            )

            openrouter_result = await self._nodes.apply_llm_response(
                state,
                invocation=invocation,
                response=llm_response,
                trace_entry=trace_entry,
                start=start,
                llm_calls=1,
            )
            state.update(openrouter_result)
            if openrouter_result.get("errors"):
                yield {"type": "error", "message": "; ".join(openrouter_result.get("errors", []))}
                yield {"type": "done"}
                return

            yield {"type": "status", "status": "explaining"}
            yield {"type": "status", "status": "evaluating"}
            final_state = await self._nodes.run_post_llm_pipeline(
                state,
                cancel_check=cancel_check,
                assistant_ids_before=assistant_ids_before,
            )
            if final_state.get("cancelled"):
                yield {"type": "error", "message": "Stream cancelled."}
                yield {"type": "done"}
                return

            response = self._build_chat_response(final_state, pipeline_start, resolved_max_tokens)
            stream_meta = self._build_stream_metadata(
                final_state,
                response,
                finish_reason=finish_reason,
                cache_hit=False,
                action="stream",
            )
            yield {"type": "complete", "response": response.model_dump(mode="json"), "stream_meta": stream_meta}
            yield {"type": "done"}
        except StreamCancelledError:
            yield {"type": "error", "message": "Stream cancelled."}
            yield {"type": "done"}
        except Exception as exc:
            logger.exception("execute_stream_failed", extra={"workflow_id": workflow_id})
            yield {"type": "error", "message": str(exc)}
            yield {"type": "done"}

    @staticmethod
    def _build_stream_metadata(
        final_state: dict[str, Any],
        response: ChatResponse,
        *,
        finish_reason: str | None,
        cache_hit: bool,
        action: str,
    ) -> dict[str, Any]:
        planner = final_state.get("planner_output") or {}
        modules_to_run = final_state.get("modules_to_run") or planner.get("modules") or []
        if isinstance(modules_to_run, list) and modules_to_run and isinstance(modules_to_run[0], dict):
            modules_to_run = [item.get("value", item) for item in modules_to_run]
        expected = expected_sections_from_planner(
            [str(item) for item in modules_to_run] if modules_to_run else None,
        )
        llm_raw = final_state.get("llm_raw") if isinstance(final_state.get("llm_raw"), dict) else {}
        missing_sections = compute_missing_sections(
            expected_sections=expected,
            llm_raw=llm_raw,
        )
        status = resolve_message_status(
            finish_reason=finish_reason,
            missing_sections=missing_sections,
            errors=final_state.get("errors"),
        )
        token_usage = final_state.get("token_usage") or {}
        return {
            "action": action,
            "status": status,
            "finish_reason": finish_reason,
            "missing_sections": missing_sections,
            "requested_sections": final_state.get("requested_sections"),
            "cache_hit": cache_hit,
            "retry_count": int(token_usage.get("llm_calls", 1)) - 1,
            "generation_type": action,
            "section_tokens": final_state.get("section_tokens") or token_usage.get("section_tokens"),
        }

    def _build_chat_response(
        self,
        result: dict[str, Any],
        pipeline_start: float,
        resolved_max_tokens: int,
    ) -> ChatResponse:
        total_execution_ms = int((time.perf_counter() - pipeline_start) * 1000)
        token_usage = result.get("token_usage") or {}
        planner_output = PlannerOutput.model_validate(result.get("planner_output") or {})
        module_outputs = [
            ModuleResponse.model_validate(item) for item in (result.get("module_responses") or [])
        ]
        regenerated = result.get("regenerated_sections")
        module_outputs = _filter_modules_for_sections(module_outputs, regenerated)

        status_map = {
            WorkflowStatus.COMPLETED.value: SessionStatus.COMPLETED,
            WorkflowStatus.PARTIAL.value: SessionStatus.COMPLETED,
            WorkflowStatus.FAILED.value: SessionStatus.FAILED,
        }
        session_status = status_map.get(
            result.get("status", WorkflowStatus.COMPLETED.value),
            SessionStatus.COMPLETED,
        )
        section_tokens = result.get("section_tokens") or token_usage.get("section_tokens") or None

        return ChatResponse(
            session_id=UUID(result["session_id"]),
            status=session_status,
            planner=planner_output,
            modules=module_outputs,
            model=str(token_usage.get("model")) if token_usage.get("model") else None,
            provider=str(token_usage.get("provider")) if token_usage.get("provider") else None,
            input_tokens=int(token_usage.get("input_tokens", 0)),
            output_tokens=int(token_usage.get("output_tokens", 0)),
            total_tokens=int(token_usage.get("total_tokens", 0)),
            latency_ms=int(result.get("latency_ms", 0)),
            execution_time_ms=total_execution_ms,
            estimated_cost=float(token_usage.get("estimated_cost_usd", 0)),
            section_tokens=section_tokens if isinstance(section_tokens, dict) else None,
            regenerated_sections=list(regenerated) if regenerated else None,
        )


def _filter_modules_for_sections(
    modules: list[ModuleResponse],
    regenerated: list[str] | None,
) -> list[ModuleResponse]:
    """Return only modules corresponding to regenerated sections (when set)."""
    if not regenerated:
        return modules
    requested_top = {s for s in regenerated if s in TOP_LEVEL_SECTIONS}
    if not requested_top:
        # Nested-only regen: keep teacher (carries feature nested payload).
        return [m for m in modules if m.module.value == "teacher"]
    return [m for m in modules if m.module.value in requested_top]
