"""Pydantic schemas for the LeetCode agent API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.enums import AgentName, MessageRole, SessionStatus


class AnalyzeRequest(BaseModel):
    """Request to analyze a LeetCode problem."""

    problem_url: HttpUrl | None = Field(
        default=None,
        description="LeetCode problem URL, e.g. https://leetcode.com/problems/two-sum/",
    )
    problem_statement: str | None = Field(
        default=None,
        min_length=20,
        description="Manual problem statement when URL fetch fails.",
    )
    title: str | None = Field(default=None, min_length=1, max_length=500)
    model_id: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    requested_sections: list[str] | None = Field(
        default=None,
        description='Incremental generation, e.g. ["teacher", "coder"].',
    )
    prior_response: dict | None = Field(
        default=None,
        description="Prior unified LLM payload for section reuse.",
    )

    @field_validator("model_id")
    @classmethod
    def strip_model_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("mode_id")
    @classmethod
    def strip_mode_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def require_url_or_statement(self) -> AnalyzeRequest:
        if self.problem_url is None and not self.problem_statement:
            msg = "Either problem_url or problem_statement must be provided."
            raise ValueError(msg)
        return self


class ProblemExample(BaseModel):
    """A single example test case."""

    input: str
    output: str
    explanation: str | None = None


class ProblemData(BaseModel):
    """Normalized LeetCode problem information."""

    title: str
    slug: str
    url: str
    description: str
    difficulty: str | None = None
    examples: list[ProblemExample] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    problem_statement_markdown: str | None = Field(
        default=None,
        description="LeetCode-style markdown for the problem statement.",
    )


class PlannerOutput(BaseModel):
    """Structured planner agent response."""

    problem_category: str
    difficulty: str
    patterns: list[str]
    execution_plan: list[str]


class CoderSolution(BaseModel):
    """A single coded solution variant."""

    approach: str
    language: str
    code: str
    explanation: str


class CoderOutput(BaseModel):
    """Structured coder agent response."""

    brute_force: CoderSolution | None = None
    better: CoderSolution | None = None
    optimal: CoderSolution | None = None


class CodeExplainerSolution(BaseModel):
    label: str
    language: str
    beginner: dict
    intermediate: dict
    interview: dict
    time_complexity: str | None = None
    space_complexity: str | None = None


class CodeExplainerOutput(BaseModel):
    solutions: list[CodeExplainerSolution] = Field(default_factory=list)
    languages_supported: list[str] = Field(default_factory=list)


class EvaluatorOutput(BaseModel):
    """Structured evaluator agent response."""

    time_complexity: str
    space_complexity: str
    optimizations: list[str]
    common_mistakes: list[str]
    edge_cases: list[str]
    interview_follow_ups: list[str]


class ManualInputRequiredResponse(BaseModel):
    """Returned when the problem cannot be fetched automatically."""

    session_id: UUID
    status: SessionStatus
    message: str
    instructions: list[str]


class AnalyzeResponse(BaseModel):
    """Full multi-agent analysis response."""

    session_id: UUID
    status: SessionStatus
    mode_id: str | None = None
    problem: ProblemData
    planner: PlannerOutput
    teacher: str
    code_explainer: CodeExplainerOutput
    coder: CoderOutput
    evaluator: EvaluatorOutput
    total_tokens: int
    total_execution_time_ms: int


class ChatMessageResponse(BaseModel):
    """Persisted chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    agent_name: AgentName | None
    message: str
    created_at: datetime


class SessionSummaryResponse(BaseModel):
    """Summary of a LeetCode session for history listing."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    problem_title: str | None
    problem_slug: str | None
    problem_url: str | None
    difficulty: str | None
    category: str | None
    status: SessionStatus
    model_id: str | None = None
    mode_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LeetCodeHistoryItemResponse(BaseModel):
    """Frontend-compatible session summary for the sidebar."""

    session_id: UUID
    title: str
    model_id: str | None = None
    mode_id: str | None = None
    created_at: datetime
    updated_at: datetime


class LeetCodeHistoryListResponse(BaseModel):
    """Paginated history list matching the frontend ApiPaginatedResponse shape."""

    items: list[LeetCodeHistoryItemResponse]
    page: int
    page_size: int
    total: int


class LeetCodeModeResponse(BaseModel):
    """Coaching mode for the LeetCode workspace header."""

    id: str
    label: str
    description: str | None = None
    icon: str | None = None
    recommended: bool = False


class LeetCodeExampleResponse(BaseModel):
    """Starter problem card for the LeetCode hero section."""

    id: str
    title: str
    difficulty: str
    pattern: str
    url: str
    icon: str | None = None


class SessionDetailResponse(BaseModel):
    """Full session with conversation history."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    problem_title: str | None
    problem_slug: str | None
    problem_url: str | None
    difficulty: str | None
    category: str | None
    status: SessionStatus
    model_id: str | None = None
    mode_id: str | None = None
    problem_description: str | None
    messages: list[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime


class UpdateSessionRequest(BaseModel):
    """Partial update for a LeetCode session (e.g. selected model or mode)."""

    model_id: str | None = Field(default=None, min_length=1, max_length=255)
    mode_id: str | None = Field(default=None, min_length=1, max_length=50)

    @field_validator("model_id")
    @classmethod
    def strip_model_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            msg = "model_id must not be empty."
            raise ValueError(msg)
        return stripped

    @field_validator("mode_id")
    @classmethod
    def strip_mode_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            msg = "mode_id must not be empty."
            raise ValueError(msg)
        return stripped

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> UpdateSessionRequest:
        if self.model_id is None and self.mode_id is None:
            msg = "At least one field must be provided (model_id or mode_id)."
            raise ValueError(msg)
        return self


class ProgressResponse(BaseModel):
    """User LeetCode practice progress."""

    model_config = ConfigDict(from_attributes=True)

    problems_attempted: int
    problems_completed: int
    easy_count: int
    medium_count: int
    hard_count: int
    current_streak: int
    longest_streak: int
    favorite_pattern: str | None
    weak_topics: list[str]
    strong_topics: list[str]
    updated_at: datetime


class DeleteSessionResponse(BaseModel):
    """Confirmation of session deletion."""

    message: str = "Session deleted successfully."


class ExportRequest(BaseModel):
    """Export a LeetCode analysis session."""

    session_id: UUID


class ExportResponse(BaseModel):
    session_id: UUID
    format: str
    filename: str
    content: str
    content_type: str


class VersionHistoryItem(BaseModel):
    message_id: UUID
    created_at: datetime
    status: str
    regenerated_from_message_id: UUID | None = None
    is_current: bool


class FollowUpRequest(BaseModel):
    """Follow-up question within an existing LeetCode session."""

    session_id: UUID
    question: str = Field(..., min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()

    @field_validator("mode_id")
    @classmethod
    def strip_mode_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class FollowUpResponse(BaseModel):
    """Follow-up response for a LeetCode session."""

    session_id: UUID
    intent: str
    teacher: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    context_match: bool = True
    rejected: bool = False


class LeetCodeAgentInfoResponse(BaseModel):
    """Declared LeetCode pipeline agent metadata."""

    role: str
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: str | None = None
    prompt_module: str | None = None
    shared_path: str
