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
