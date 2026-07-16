"""Generic AI platform API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AIFeature, ExecutionMode, MessageRole, ModuleName, SessionStatus


class ChatRequest(BaseModel):
    """Generic chat request for any AI product."""

    feature: AIFeature
    message: str = Field(..., min_length=1, max_length=32000)
    session_id: UUID | None = None
    title: str | None = Field(default=None, max_length=500)
    context: dict[str, Any] | None = None
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # Optional client override. When omitted/null, FEATURE_MAX_TOKENS for the
    # current feature is used (never a single global default).
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    # Incremental generation: regenerate only these logical sections.
    # Example: ["teacher", "practice"]. Unchanged sections are reused.
    requested_sections: list[str] | None = Field(default=None)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()

    @field_validator("requested_sections")
    @classmethod
    def normalize_sections(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip().lower() for item in value if item and item.strip()]
        return cleaned or None


class PlannerOutput(BaseModel):
    """Deterministic planner output."""

    feature: AIFeature
    modules: list[ModuleName]
    execution_mode: ExecutionMode
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModuleResponse(BaseModel):
    """Formatted output from a processing module."""

    module: ModuleName
    content: str
    structured: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    """Generic chat response."""

    session_id: UUID
    status: SessionStatus
    planner: PlannerOutput
    modules: list[ModuleResponse]
    model: str | None = None
    provider: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    estimated_cost: float = 0.0
    # Tokens attributed to each logical section (estimated from payload size).
    section_tokens: dict[str, int] | None = None
    # Sections that were regenerated in this request (None = full generation).
    regenerated_sections: list[str] | None = None


class MessageResponse(BaseModel):
    """Single message in session history."""

    id: UUID
    role: MessageRole
    module_name: ModuleName | None
    content: str
    content_metadata: dict[str, Any] | None
    created_at: datetime


class SessionSummaryResponse(BaseModel):
    """Summary of an AI session."""

    id: UUID
    feature: AIFeature
    title: str | None
    status: SessionStatus
    summary: str | None
    model_id: str | None = None
    mode_id: str | None = None
    is_archived: bool = False
    is_pinned: bool = False
    last_active_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ConversationMemoryResponse(BaseModel):
    """Conversation memory snapshot for a session."""

    session_id: UUID
    summary: str | None = None
    context: dict[str, Any] | None = None
    recent_messages: list[dict[str, Any]] | None = None
    previous_responses: list[str] | None = None
    follow_up_questions: list[str] | None = None
    memory_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SessionDetailResponse(BaseModel):
    """Full session detail with messages and memory."""

    session: SessionSummaryResponse
    messages: list[MessageResponse]
    total_messages: int
    memory: ConversationMemoryResponse | None = None
    teacher_responses: list[ModuleResponse] = Field(default_factory=list)
    follow_up_messages: list[MessageResponse] = Field(default_factory=list)


class FollowUpRequest(BaseModel):
    """Follow-up question request."""

    session_id: UUID
    question: str = Field(..., min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    # When set, only regenerate these sections (reuse the rest from session).
    requested_sections: list[str] | None = Field(default=None)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()

    @field_validator("requested_sections")
    @classmethod
    def normalize_followup_sections(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip().lower() for item in value if item and item.strip()]
        return cleaned or None


class FollowUpResponse(BaseModel):
    """Follow-up question response."""

    session_id: UUID
    intent: str
    teacher: ModuleResponse
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0
    context_match: bool = True
    rejected: bool = False


class SummarizeResponse(BaseModel):
    """Conversation summary response."""

    session_id: UUID
    summary: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    execution_time_ms: int = 0


class HistoryListResponse(BaseModel):
    """Paginated session history."""

    sessions: list[SessionSummaryResponse]
    total: int
    limit: int
    offset: int


class ModelInfo(BaseModel):
    """Available LLM model metadata for the frontend model selector."""

    id: str
    name: str
    provider: str
    description: str | None = None
    recommended: bool = False
    default: bool = False
    enabled: bool = True
    tier: str | None = None
    context_window: int | None = None
    supports_vision: bool = False
    supports_streaming: bool = True
    cost_per_1k_input: float | None = None
    cost_per_1k_output: float | None = None


class ModelsResponse(BaseModel):
    """List of available models."""

    models: list[ModelInfo]
    default_model: str
