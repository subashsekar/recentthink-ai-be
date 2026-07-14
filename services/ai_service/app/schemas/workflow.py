"""LangGraph workflow state definitions."""

from typing import Any, TypedDict
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import SessionStatus, WorkflowStatus
from app.schemas.ai import PlannerOutput


class TokenUsage(BaseModel):
    """Token usage metadata for a workflow execution."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    temperature: float = 0.2
    estimated_cost_usd: float = 0.0
    estimated_cost_inr: float = 0.0


class TraceEntry(BaseModel):
    """Single node execution trace entry."""

    node_name: str
    status: str
    execution_time_ms: int = 0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    error_message: str | None = None


class AIWorkflowStateModel(BaseModel):
    """Serializable workflow state for API responses and persistence."""

    workflow_id: UUID
    session_id: UUID
    user_id: UUID
    feature_name: str
    problem: dict[str, Any] = Field(default_factory=dict)
    planner_output: PlannerOutput | None = None
    teacher_output: dict[str, Any] | None = None
    coder_output: dict[str, Any] | None = None
    code_explainer_output: dict[str, Any] | None = None
    evaluator_output: dict[str, Any] | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    execution_time_ms: int = 0
    latency_ms: int = 0
    errors: list[str] = Field(default_factory=list)
    trace: list[TraceEntry] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING


class AIWorkflowState(TypedDict, total=False):
    """Typed state passed through the LangGraph pipeline."""

    workflow_id: str
    session_id: str
    user_id: str
    feature_name: str
    problem: dict[str, Any]
    message: str
    title: str | None
    context: dict[str, Any] | None
    model: str | None
    mode_id: str | None
    temperature: float
    max_tokens: int
    memory_context: dict[str, Any]
    planner_output: dict[str, Any] | None
    llm_raw: dict[str, Any] | None
    teacher_output: dict[str, Any] | None
    coder_output: dict[str, Any] | None
    code_explainer_output: dict[str, Any] | None
    evaluator_output: dict[str, Any] | None
    module_responses: list[dict[str, Any]]
    token_usage: dict[str, Any]
    section_tokens: dict[str, int]
    requested_sections: list[str] | None
    regenerated_sections: list[str] | None
    execution_time_ms: int
    latency_ms: int
    errors: list[str]
    trace: list[dict[str, Any]]
    status: str
    modules_to_run: list[str]
    session_status: str
