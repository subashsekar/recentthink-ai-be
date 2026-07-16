"""Schemas for AI Service internal admin APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AIAnalyticsResponse(BaseModel):
    total_ai_sessions: int = 0
    leetcode_sessions: int = 0
    hackerrank_sessions: int = 0
    dsa_sessions: int = 0
    courses_generated: int = 0
    total_conversations: int = 0
    average_response_time: float = 0.0
    average_tokens: float = 0.0
    average_cost: float = 0.0


class ProviderUsageItem(BaseModel):
    provider: str
    requests: int
    tokens: int
    estimated_cost: float


class ModelUsageItem(BaseModel):
    model: str
    requests: int
    tokens: int
    estimated_cost: float


class ModelAnalyticsResponse(BaseModel):
    provider_usage: list[ProviderUsageItem] = Field(default_factory=list)
    model_usage: list[ModelUsageItem] = Field(default_factory=list)


class AIUserHistoryResponse(BaseModel):
    sessions: list[dict] = Field(default_factory=list)
    usage: list[dict] = Field(default_factory=list)


class UserPurgeResponse(BaseModel):
    user_id: str
    sessions_deleted: int = 0
    leetcode_progress: int = 0
    hackerrank_progress: int = 0
    course_progress: int = 0
    pattern_progress: int = 0
    pattern_mastery: int = 0
    course_bookmarks: int = 0
    pattern_bookmarks: int = 0


class PromptVersionResponse(BaseModel):
    id: UUID
    feature: str
    module_name: str
    version: str
    locale: str
    content: str
    is_active: bool
    created_at: datetime


class PromptUpsertRequest(BaseModel):
    feature: str = Field(..., min_length=1, max_length=100)
    module_name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    locale: str = Field(default="en", min_length=1, max_length=20)
    is_active: bool = True
