"""Maps between LeetCode API schemas and shared AI platform schemas."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.agents.leetcode.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ChatMessageResponse,
    CodeExplainerOutput,
    CoderOutput,
    CoderSolution,
    EvaluatorOutput,
    FollowUpResponse,
    LeetCodeHistoryItemResponse,
    LeetCodeHistoryListResponse,
    PlannerOutput,
    ProblemData,
    SessionDetailResponse,
    SessionSummaryResponse,
)
from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.enums import AgentName, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import ChatResponse, FollowUpResponse as PlatformFollowUpResponse
from app.schemas.ai import SessionDetailResponse as PlatformSessionDetailResponse


def _module_response(chat: ChatResponse, module: ModuleName) -> dict[str, Any] | None:
    for item in chat.modules:
        if item.module == module:
            return item.structured or {}
    return None


def _to_coder_solution(raw: dict[str, Any] | None, *, default_approach: str) -> CoderSolution | None:
    if not isinstance(raw, dict) or not raw.get("code"):
        return None
    return CoderSolution(
        approach=str(raw.get("approach") or default_approach),
        language=str(raw.get("language") or "python"),
        code=str(raw.get("code") or ""),
        explanation=str(raw.get("explanation") or ""),
    )


def _solutions_array_to_structured(payload: dict[str, Any]) -> dict[str, Any]:
    """Map a legacy solutions[] array into brute/better/optimal slots."""
    solutions = payload.get("solutions") or []
    if not isinstance(solutions, list) or not solutions:
        return payload
    if any(payload.get(key) for key in ("brute_force", "better_solution", "optimal_solution", "better", "optimal")):
        return payload
    labels = ("brute_force", "better_solution", "optimal_solution")
    defaults = ("Brute Force", "Better Solution", "Optimal Solution")
    updated = dict(payload)
    for index, raw in enumerate(solutions[:3]):
        if not isinstance(raw, dict) or not raw.get("code"):
            continue
        updated[labels[index]] = {
            "approach": raw.get("approach") or defaults[index],
            "language": raw.get("language") or payload.get("language") or "python",
            "code": raw.get("code"),
            "explanation": raw.get("explanation") or "",
            "complexity": raw.get("complexity") or "",
        }
    return updated


def to_coder_output(structured: dict[str, Any] | None) -> CoderOutput:
    payload = _solutions_array_to_structured(structured or {})
    better_raw = payload.get("better_solution") or payload.get("better")
    optimal_raw = payload.get("optimal_solution") or payload.get("optimal")
    return CoderOutput(
        brute_force=_to_coder_solution(payload.get("brute_force"), default_approach="Brute Force"),
        better=_to_coder_solution(better_raw, default_approach="Better Solution"),
        optimal=_to_coder_solution(optimal_raw, default_approach="Optimal Solution"),
    )


def to_evaluator_output(structured: dict[str, Any] | None) -> EvaluatorOutput:
    payload = structured or {}
    follow_ups = payload.get("follow_up_questions") or payload.get("interview_questions") or []
    return EvaluatorOutput(
        time_complexity=str(payload.get("time_complexity") or "Unknown"),
        space_complexity=str(payload.get("space_complexity") or "Unknown"),
        optimizations=list(payload.get("optimizations") or []),
        common_mistakes=list(payload.get("mistakes") or payload.get("common_mistakes") or []),
        edge_cases=list(payload.get("edge_cases") or []),
        interview_follow_ups=[str(item) for item in follow_ups],
    )


def to_code_explainer_output(structured: dict[str, Any] | None) -> CodeExplainerOutput:
    payload = structured or {}
    return CodeExplainerOutput.model_validate(payload)


def to_planner_output(chat: ChatResponse, problem: ProblemData) -> PlannerOutput:
    metadata = chat.planner.metadata or {}
    topics = problem.topics or metadata.get("patterns") or []
    category = (
        metadata.get("problem_category")
        or (topics[0] if topics else None)
        or problem.title
    )
    return PlannerOutput(
        problem_category=str(category),
        difficulty=str(metadata.get("difficulty") or problem.difficulty or "Unknown"),
        patterns=[str(item) for item in (metadata.get("patterns") or topics)],
        execution_plan=[str(item) for item in (metadata.get("execution_plan") or [])],
    )


def to_analyze_response(
    chat: ChatResponse,
    problem: ProblemData,
    *,
    mode_id: str | None = None,
) -> AnalyzeResponse:
    teacher_module = next((m for m in chat.modules if m.module == ModuleName.TEACHER), None)
    coder_structured = _module_response(chat, ModuleName.CODER)
    code_explainer_structured = _module_response(chat, ModuleName.CODE_EXPLAINER)
    evaluator_structured = _module_response(chat, ModuleName.EVALUATOR)
    return AnalyzeResponse(
        session_id=chat.session_id,
        status=chat.status,
        mode_id=mode_id,
        problem=problem,
        planner=to_planner_output(chat, problem),
        teacher=teacher_module.content if teacher_module else "",
        code_explainer=to_code_explainer_output(code_explainer_structured),
        coder=to_coder_output(coder_structured),
        evaluator=to_evaluator_output(evaluator_structured),
        total_tokens=chat.total_tokens,
        total_execution_time_ms=chat.execution_time_ms,
    )


def _problem_from_context(context: dict[str, Any] | None) -> dict[str, Any]:
    return context or {}


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def to_session_summary(session: AISession) -> SessionSummaryResponse:
    context = _problem_from_context(session.context_metadata)
    return SessionSummaryResponse(
        id=session.id,
        problem_title=session.title or context.get("title"),
        problem_slug=context.get("slug"),
        problem_url=context.get("url"),
        difficulty=context.get("difficulty"),
        category=(context.get("topics") or [None])[0] if context.get("topics") else None,
        status=session.status,
        model_id=_optional_str(session.model_id),
        mode_id=_optional_str(session.mode_id),
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def to_history_item(session: AISession) -> LeetCodeHistoryItemResponse:
    summary = to_session_summary(session)
    return LeetCodeHistoryItemResponse(
        session_id=summary.id,
        title=summary.problem_title or "Untitled Session",
        model_id=summary.model_id,
        mode_id=summary.mode_id,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
    )


def _to_agent_name(module_name: ModuleName | None) -> AgentName | None:
    if module_name is None:
        return None
    mapping = {
        ModuleName.PLANNER: AgentName.PLANNER,
        ModuleName.TEACHER: AgentName.TEACHER,
        ModuleName.CODER: AgentName.CODER,
        ModuleName.CODE_EXPLAINER: AgentName.CODE_EXPLAINER,
        ModuleName.EVALUATOR: AgentName.EVALUATOR,
    }
    return mapping.get(module_name)


def _to_chat_message(message: AIMessage) -> ChatMessageResponse:
    return ChatMessageResponse(
        id=message.id,
        role=message.role,
        agent_name=_to_agent_name(message.module_name),
        message=message.content,
        created_at=message.created_at,
    )


def to_session_detail(detail: PlatformSessionDetailResponse) -> SessionDetailResponse:
    problem_context: dict[str, Any] = {}
    if detail.memory and detail.memory.context:
        memory_context = detail.memory.context
        raw_problem = memory_context.get("problem")
        if isinstance(raw_problem, dict):
            problem_context = raw_problem
        elif isinstance(memory_context, dict) and memory_context.get("title"):
            problem_context = memory_context
    return SessionDetailResponse(
        id=detail.session.id,
        problem_title=detail.session.title or problem_context.get("title"),
        problem_slug=problem_context.get("slug"),
        problem_url=problem_context.get("url"),
        difficulty=problem_context.get("difficulty"),
        category=(problem_context.get("topics") or [None])[0] if problem_context.get("topics") else None,
        status=detail.session.status,
        model_id=detail.session.model_id,
        mode_id=detail.session.mode_id,
        problem_description=problem_context.get("description"),
        messages=[_to_chat_message(message) for message in detail.messages],
        created_at=detail.session.created_at,
        updated_at=detail.session.updated_at,
    )


def to_follow_up_response(response: PlatformFollowUpResponse) -> FollowUpResponse:
    return FollowUpResponse(
        session_id=response.session_id,
        intent=response.intent,
        teacher=response.teacher.content,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        total_tokens=response.total_tokens,
        latency_ms=response.latency_ms,
        execution_time_ms=response.execution_time_ms,
    )


def build_chat_message(problem: ProblemData) -> str:
    return f"Analyze problem: {problem.url}"

def build_problem_context(problem: ProblemData) -> dict[str, Any]:
    return problem.model_dump()
