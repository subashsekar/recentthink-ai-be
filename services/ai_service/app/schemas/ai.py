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
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=128000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


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
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=32000)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()


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
    """Available LLM model metadata."""

    id: str
    provider: str
    description: str | None = None
    is_default: bool = False


class ModelsResponse(BaseModel):
    """List of available models."""

    models: list[ModelInfo]
    default_model: str
