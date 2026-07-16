"""Pydantic schemas for the HackerRank agent API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

from app.models.enums import AgentName, MessageRole, SessionStatus


class AnalyzeRequest(BaseModel):
    """Request to analyze a HackerRank challenge."""

    problem_url: HttpUrl | None = Field(
        default=None,
        description="HackerRank challenge URL, e.g. https://www.hackerrank.com/challenges/two-strings/problem",
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
        description='Incremental generation, e.g. ["teacher", "practice"].',
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
    input: str
    output: str
    explanation: str | None = None


class ProblemData(BaseModel):
    """Normalized HackerRank challenge information."""

    title: str
    slug: str
    url: str
    description: str
    difficulty: str | None = None
    examples: list[ProblemExample] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    domain: str | None = None
    languages: list[str] = Field(default_factory=list)
    problem_statement_markdown: str | None = None


class PlannerOutput(BaseModel):
    problem_category: str
    difficulty: str
    patterns: list[str]
    execution_plan: list[str]
    problem_domain: str | None = None
    learning_objectives: list[str] = Field(default_factory=list)


class CoderSolution(BaseModel):
    approach: str
    language: str
    code: str
    explanation: str


class CoderOutput(BaseModel):
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
    time_complexity: str
    space_complexity: str
    optimizations: list[str]
    common_mistakes: list[str]
    edge_cases: list[str]
    interview_follow_ups: list[str]


class ManualInputRequiredResponse(BaseModel):
    session_id: UUID
    status: SessionStatus
    message: str
    instructions: list[str]


class AnalyzeResponse(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    agent_name: AgentName | None
    message: str
    created_at: datetime


class SessionSummaryResponse(BaseModel):
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


class HackerrankHistoryItemResponse(BaseModel):
    session_id: UUID
    title: str
    model_id: str | None = None
    mode_id: str | None = None
    created_at: datetime
    updated_at: datetime


class HackerrankHistoryListResponse(BaseModel):
    items: list[HackerrankHistoryItemResponse]
    page: int
    page_size: int
    total: int


class HackerrankModeResponse(BaseModel):
    """Coaching mode for the HackerRank workspace header."""

    id: str
    label: str
    description: str | None = None
    icon: str | None = None
    recommended: bool = False


class SessionDetailResponse(BaseModel):
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
    message: str = "Session deleted successfully."


class ExportRequest(BaseModel):
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
    session_id: UUID
    intent: str
    teacher: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0


class HackerrankAgentInfoResponse(BaseModel):
    role: str
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: str | None = None
    prompt_module: str | None = None
    shared_path: str


class HackerrankExampleResponse(BaseModel):
    id: str
    title: str
    difficulty: str
    domain: str
    url: str
    icon: str | None = None
