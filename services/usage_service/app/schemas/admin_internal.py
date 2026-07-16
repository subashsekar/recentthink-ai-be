"""Schemas for Usage Service internal admin APIs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class FeatureUsageItem(BaseModel):
    feature: str
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0
    average_time_ms: float = 0.0
    average_tokens: float = 0.0
    average_cost: float = 0.0


class ModelUsageItem(BaseModel):
    model: str
    provider: str | None = None
    requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    average_latency_ms: float = 0.0
    success_rate: float = 1.0
    failure_rate: float = 0.0


class ProviderUsageItem(BaseModel):
    provider: str
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0


class TopUserItem(BaseModel):
    user_id: UUID
    total_tokens: int = 0
    total_requests: int = 0
    estimated_cost: float = 0.0


class UsageAnalyticsResponse(BaseModel):
    """Legacy platform summary (kept for backward compatibility)."""

    total_requests: int = 0
    daily_requests: int = 0
    monthly_requests: int = 0
    token_usage: int = 0
    top_features: list[FeatureUsageItem] = Field(default_factory=list)


class AnalyticsDashboardResponse(BaseModel):
    total_requests: int = 0
    total_ai_sessions: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens_used: int = 0
    total_estimated_cost: float = 0.0
    average_tokens_per_request: float = 0.0
    average_cost_per_request: float = 0.0
    todays_usage: dict[str, Any] = Field(default_factory=dict)
    weekly_usage: dict[str, Any] = Field(default_factory=dict)
    monthly_usage: dict[str, Any] = Field(default_factory=dict)
    # Platform statistics strip
    platform_total_tokens: int = 0
    platform_total_cost: float = 0.0
    platform_total_requests: int = 0
    active_users_today: int = 0
    most_active_user: TopUserItem | None = None
    most_used_ai_feature: str | None = None
    most_used_ai_model: str | None = None
    most_used_provider: str | None = None
    average_response_time_ms: float = 0.0
    average_execution_time_ms: float = 0.0


class TokenAnalyticsResponse(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    daily_tokens: int = 0
    weekly_tokens: int = 0
    monthly_tokens: int = 0
    top_users: list[TopUserItem] = Field(default_factory=list)
    top_features: list[FeatureUsageItem] = Field(default_factory=list)
    top_models: list[ModelUsageItem] = Field(default_factory=list)
    top_providers: list[ProviderUsageItem] = Field(default_factory=list)
    # Aggregated completion tokens by logical section (teacher/coder/practice/…).
    section_token_totals: dict[str, int] = Field(default_factory=dict)


class ModelAnalyticsListResponse(BaseModel):
    items: list[ModelUsageItem] = Field(default_factory=list)


class ProviderAnalyticsListResponse(BaseModel):
    items: list[ProviderUsageItem] = Field(default_factory=list)


class FeatureAnalyticsListResponse(BaseModel):
    items: list[FeatureUsageItem] = Field(default_factory=list)


class UserUsageRow(BaseModel):
    user_id: UUID
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    average_tokens_per_request: float = 0.0
    last_active: str | None = None
    most_used_feature: str | None = None
    most_used_model: str | None = None


class UserUsageListResponse(BaseModel):
    items: list[UserUsageRow] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class UserUsageDetailResponse(BaseModel):
    user_id: UUID
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    average_tokens_per_request: float = 0.0
    average_execution_time_ms: float = 0.0
    last_activity: str | None = None
    most_used_feature: str | None = None
    most_used_model: str | None = None
    feature_breakdown: list[FeatureUsageItem] = Field(default_factory=list)
    model_usage: list[ModelUsageItem] = Field(default_factory=list)
    provider_usage: list[ProviderUsageItem] = Field(default_factory=list)
    session_history: list[dict[str, Any]] = Field(default_factory=list)
    recent_conversations: list[dict[str, Any]] = Field(default_factory=list)


class ChartSeriesPoint(BaseModel):
    label: str
    value: float = 0.0


class ChartsResponse(BaseModel):
    daily_token_usage: list[ChartSeriesPoint] = Field(default_factory=list)
    weekly_token_usage: list[ChartSeriesPoint] = Field(default_factory=list)
    monthly_token_usage: list[ChartSeriesPoint] = Field(default_factory=list)
    requests_per_day: list[ChartSeriesPoint] = Field(default_factory=list)
    top_features: list[ChartSeriesPoint] = Field(default_factory=list)
    top_models: list[ChartSeriesPoint] = Field(default_factory=list)
    top_providers: list[ChartSeriesPoint] = Field(default_factory=list)
    top_users: list[ChartSeriesPoint] = Field(default_factory=list)
    cost_per_day: list[ChartSeriesPoint] = Field(default_factory=list)
    tokens_per_feature: list[ChartSeriesPoint] = Field(default_factory=list)


class CostAnalyticsResponse(BaseModel):
    total_estimated_cost: float = 0.0
    average_cost_per_request: float = 0.0
    daily_cost: float = 0.0
    weekly_cost: float = 0.0
    monthly_cost: float = 0.0
    cost_by_feature: list[FeatureUsageItem] = Field(default_factory=list)
    cost_by_model: list[ModelUsageItem] = Field(default_factory=list)
    cost_by_provider: list[ProviderUsageItem] = Field(default_factory=list)
    cost_per_day: list[ChartSeriesPoint] = Field(default_factory=list)


class BatchUserStatsResponse(BaseModel):
    items: list[UserUsageRow] = Field(default_factory=list)


class UserUsageResponse(BaseModel):
    """Legacy raw recent records for a user."""

    items: list[dict[str, Any]] = Field(default_factory=list)


class ExportPayloadResponse(BaseModel):
    report: str
    rows: list[dict[str, Any]] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)


class UserPurgeResponse(BaseModel):
    user_id: str
    records_deleted: int = 0

