"""Admin Service API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DashboardResponse(BaseModel):
    total_users: int = 0
    active_users: int = 0
    new_users_today: int = 0
    verified_users: int = 0
    blocked_users: int = 0
    students: int = 0
    professionals: int = 0
    job_seekers: int = 0
    # Platform AI usage strip (from Usage Service)
    platform_total_tokens: int = 0
    platform_total_cost: float = 0.0
    platform_total_requests: int = 0
    active_users_today: int = 0
    most_active_user: dict | None = None
    most_used_ai_feature: str | None = None
    most_used_ai_model: str | None = None
    most_used_provider: str | None = None
    average_response_time: float = 0.0
    average_execution_time: float = 0.0


class AdminUserItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: str
    is_verified: bool
    is_active: bool
    is_blocked: bool
    disabled_at: datetime | None = None
    blocked_at: datetime | None = None
    blocked_reason: str | None = None
    created_at: datetime | None = None
    username: str | None = None
    current_status: str | None = None
    primary_skill: str | None = None
    profile_picture_url: str | None = None
    # Usage Service enrichment
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    last_ai_activity: datetime | None = None
    most_used_feature: str | None = None
    most_used_model: str | None = None
    current_plan: str | None = None


class UserListResponse(BaseModel):
    items: list[AdminUserItem]
    total: int
    page: int
    page_size: int


class UserDetailResponse(BaseModel):
    user: AdminUserItem
    profile: dict | None = None
    statistics: dict | None = None
    ai_history: dict | None = None
    usage: dict | None = None
    usage_analytics: dict | None = None


class ReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class MutationResponse(BaseModel):
    message: str
    user: AdminUserItem | None = None


class AnalyticsResponse(BaseModel):
    total_ai_sessions: int = 0
    leetcode_sessions: int = 0
    hackerrank_sessions: int = 0
    dsa_sessions: int = 0
    courses_generated: int = 0
    total_conversations: int = 0
    average_response_time: float = 0.0
    average_tokens: float = 0.0
    average_cost: float = 0.0


class UsageAnalyticsResponse(BaseModel):
    total_requests: int = 0
    daily_requests: int = 0
    monthly_requests: int = 0
    token_usage: int = 0
    top_features: list[dict] = Field(default_factory=list)
    provider_usage: list[dict] = Field(default_factory=list)
    model_usage: list[dict] = Field(default_factory=list)
    estimated_cost: float = 0.0


class ModelAnalyticsResponse(BaseModel):
    provider_usage: list[dict] = Field(default_factory=list)
    model_usage: list[dict] = Field(default_factory=list)


class ChartSeriesPoint(BaseModel):
    label: str
    value: float = 0.0


class AnalyticsDashboardResponse(BaseModel):
    total_requests: int = 0
    total_ai_sessions: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens_used: int = 0
    total_estimated_cost: float = 0.0
    average_tokens_per_request: float = 0.0
    average_cost_per_request: float = 0.0
    todays_usage: dict = Field(default_factory=dict)
    weekly_usage: dict = Field(default_factory=dict)
    monthly_usage: dict = Field(default_factory=dict)
    platform_total_tokens: int = 0
    platform_total_cost: float = 0.0
    platform_total_requests: int = 0
    active_users_today: int = 0
    most_active_user: dict | None = None
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
    top_users: list[dict] = Field(default_factory=list)
    top_features: list[dict] = Field(default_factory=list)
    top_models: list[dict] = Field(default_factory=list)
    top_providers: list[dict] = Field(default_factory=list)
    section_token_totals: dict[str, int] = Field(default_factory=dict)


class FeatureAnalyticsItem(BaseModel):
    feature: str
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0
    average_time_ms: float = 0.0
    average_tokens: float = 0.0
    average_cost: float = 0.0


class FeatureAnalyticsResponse(BaseModel):
    items: list[FeatureAnalyticsItem] = Field(default_factory=list)


class ModelAnalyticsItem(BaseModel):
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


class ModelAnalyticsListResponse(BaseModel):
    items: list[ModelAnalyticsItem] = Field(default_factory=list)


class ProviderAnalyticsItem(BaseModel):
    provider: str
    requests: int = 0
    tokens: int = 0
    cost: float = 0.0


class ProviderAnalyticsResponse(BaseModel):
    items: list[ProviderAnalyticsItem] = Field(default_factory=list)


class UserUsageTableItem(BaseModel):
    user_id: UUID
    user_name: str = ""
    email: str = ""
    role: str = "USER"
    current_status: str | None = None
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    average_tokens_per_request: float = 0.0
    last_active: datetime | None = None
    current_plan: str | None = None
    most_used_feature: str | None = None
    most_used_model: str | None = None


class UserUsageTableResponse(BaseModel):
    items: list[UserUsageTableItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class UserUsageDetailAdminResponse(BaseModel):
    profile: dict | None = None
    user: AdminUserItem | None = None
    total_requests: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    feature_breakdown: list[dict] = Field(default_factory=list)
    model_usage: list[dict] = Field(default_factory=list)
    provider_usage: list[dict] = Field(default_factory=list)
    session_history: list[dict] = Field(default_factory=list)
    recent_conversations: list[dict] = Field(default_factory=list)
    average_execution_time_ms: float = 0.0
    last_activity: datetime | None = None


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
    cost_by_feature: list[dict] = Field(default_factory=list)
    cost_by_model: list[dict] = Field(default_factory=list)
    cost_by_provider: list[dict] = Field(default_factory=list)
    cost_per_day: list[ChartSeriesPoint] = Field(default_factory=list)


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admin_id: UUID
    action: str
    target_user_id: UUID | None = None
    reason: str | None = None
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    page_size: int


class ServiceHealthItem(BaseModel):
    name: str
    status: str
    response_time_ms: float


class HealthResponse(BaseModel):
    services: list[ServiceHealthItem]
    overall: str


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    total: int
    page: int
    page_size: int


class MarkAllReadResponse(BaseModel):
    message: str
    updated: int


class BroadcastNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)
    type: str = Field(default="announcement", max_length=50)


class BroadcastNotificationResponse(BaseModel):
    message: str
    created: int
