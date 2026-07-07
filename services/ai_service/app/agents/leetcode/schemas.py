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
    problem: ProblemData
    planner: PlannerOutput
    teacher: str
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
    created_at: datetime
    updated_at: datetime


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
    problem_description: str | None
    messages: list[ChatMessageResponse]
    created_at: datetime
    updated_at: datetime


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


class FollowUpRequest(BaseModel):
    """Follow-up question within an existing LeetCode session."""

    session_id: UUID
    question: str = Field(..., min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=255)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


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


class LeetCodeAgentInfoResponse(BaseModel):
    """Declared LeetCode pipeline agent metadata."""

    role: str
    name: str
    description: str
    uses_openrouter: bool
    workflow_module: str | None = None
    prompt_module: str | None = None
    shared_path: str
