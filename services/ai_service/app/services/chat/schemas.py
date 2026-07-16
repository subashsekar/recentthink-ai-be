"""Conversational chat API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AIFeature, MessageRole, ModuleName, SessionStatus
from app.schemas.ai import (
    ChatResponse,
    FollowUpResponse,
    MessageResponse,
    ModuleResponse,
    SessionDetailResponse,
    SessionSummaryResponse,
)


class ChatFeatureSlug(StrEnum):
    """URL feature slugs for /chat/{feature} routes."""

    LEETCODE = "leetcode"
    HACKERRANK = "hackerrank"
    DSA_PATTERN = "dsa_pattern"
    COURSE_GENERATOR = "course_generator"
    INTERVIEW = "interview"


FEATURE_SLUG_MAP: dict[ChatFeatureSlug, AIFeature] = {
    ChatFeatureSlug.LEETCODE: AIFeature.LEETCODE,
    ChatFeatureSlug.HACKERRANK: AIFeature.HACKERRANK,
    ChatFeatureSlug.DSA_PATTERN: AIFeature.DSA_PATTERN,
    ChatFeatureSlug.COURSE_GENERATOR: AIFeature.COURSE_GENERATOR,
    ChatFeatureSlug.INTERVIEW: AIFeature.INTERVIEW,
}


class ChatStreamRequest(BaseModel):
    """Start or continue a conversational turn with streaming."""

    message: str = Field(..., min_length=1, max_length=32000)
    session_id: UUID | None = None
    title: str | None = Field(default=None, max_length=500)
    context: dict[str, Any] | None = None
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
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


class ChatContinueRequest(BaseModel):
    """Continue a truncated assistant response."""

    session_id: UUID
    message_id: UUID | None = None
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)


class ChatRetryRequest(BaseModel):
    """Retry a failed or unsatisfactory assistant response."""

    session_id: UUID
    message_id: UUID
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)


class ChatRegenerateRequest(BaseModel):
    """Regenerate an assistant response in the same session."""

    session_id: UUID
    message_id: UUID
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    requested_sections: list[str] | None = Field(default=None)

    @field_validator("requested_sections")
    @classmethod
    def normalize_sections(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip().lower() for item in value if item and item.strip()]
        return cleaned or None


class ChatFollowUpRequest(BaseModel):
    """Natural follow-up within an existing session."""

    session_id: UUID
    question: str = Field(..., min_length=1, max_length=8000)
    model: str | None = Field(default=None, max_length=255)
    mode_id: str | None = Field(default=None, max_length=50)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=32000)
    requested_sections: list[str] | None = Field(default=None)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        return value.strip()

    @field_validator("requested_sections")
    @classmethod
    def normalize_sections(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [item.strip().lower() for item in value if item and item.strip()]
        return cleaned or None


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        return value.strip()


class SessionArchiveRequest(BaseModel):
    archived: bool = True


class SessionPinRequest(BaseModel):
    pinned: bool = True


class MessageBookmarkRequest(BaseModel):
    bookmarked: bool = True


class ExportFormat(StrEnum):
    MARKDOWN = "markdown"
    PDF = "pdf"
    JSON = "json"
    TXT = "txt"


class ExportType(StrEnum):
    CONVERSATION = "conversation"
    SOLUTION = "solution"
    COURSE = "course"
    PATTERN = "pattern"
    INTERVIEW_REPORT = "interview_report"


class ChatExportRequest(BaseModel):
    session_id: UUID
    format: ExportFormat = ExportFormat.MARKDOWN
    export_type: ExportType = ExportType.CONVERSATION
    include: list[str] | None = None


class ChatExportResponse(BaseModel):
    session_id: UUID
    format: ExportFormat
    export_type: ExportType
    filename: str
    content: str
    content_type: str


class ChatActionResponse(BaseModel):
    """Non-streaming action result."""

    session_id: UUID
    message_id: UUID | None = None
    action: str
    response: ChatResponse | FollowUpResponse | None = None


class MessageActionMetadata(BaseModel):
    """Documented shape for AIMessage.content_metadata chat fields."""

    status: str | None = None
    action: str | None = None
    supersedes_message_id: str | None = None
    regenerated_from_message_id: str | None = None
    prompt_version: str | None = None
    model: str | None = None
    provider: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    execution_time_ms: int | None = None
    bookmarked: bool | None = None
    finish_reason: str | None = None
    share_token: str | None = None
    deleted: bool | None = None


__all__ = [
    "ChatActionResponse",
    "ChatContinueRequest",
    "ChatExportRequest",
    "ChatExportResponse",
    "ChatFeatureSlug",
    "ChatFollowUpRequest",
    "ChatRegenerateRequest",
    "ChatRetryRequest",
    "ChatStreamRequest",
    "ExportFormat",
    "ExportType",
    "FEATURE_SLUG_MAP",
    "MessageActionMetadata",
    "MessageBookmarkRequest",
    "SessionArchiveRequest",
    "SessionPinRequest",
    "SessionRenameRequest",
]
