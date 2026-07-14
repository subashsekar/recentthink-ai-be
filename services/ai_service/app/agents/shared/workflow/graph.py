"""LangGraph AI workflow engine."""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID, uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.shared.workflow.nodes import WorkflowNodes
from app.core.config import feature_max_tokens_map, get_ai_settings
from app.core.feature_tokens import TOP_LEVEL_SECTIONS, resolve_feature_max_tokens
from app.models.enums import SessionStatus, WorkflowStatus
from app.schemas.ai import ChatRequest, ChatResponse, ModuleResponse, PlannerOutput
from app.schemas.workflow import AIWorkflowState
from app.utils.prompt_sanitizer import sanitize_user_input
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
