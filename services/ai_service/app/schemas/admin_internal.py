"""Schemas for AI Service internal admin APIs."""

from __future__ import annotations

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
