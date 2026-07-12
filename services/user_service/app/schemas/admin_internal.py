"""Schemas for Admin Service → User Service internal APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.enums import CurrentStatus, PrimarySkill
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.profile import ProfileResponse, StatisticsResponse


class AdminDashboardProfileStats(BaseModel):
    """Profile-status counters for the admin dashboard."""

    students: int = 0
    professionals: int = 0
    job_seekers: int = 0


class AdminProfileListItem(BaseModel):
    """Compact profile row for admin enrichment."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    current_status: CurrentStatus | None = None
    primary_skill: PrimarySkill | None = None
    profile_picture_url: str | None = None


class AdminProfileListResponse(BaseModel):
    items: list[AdminProfileListItem]
    total: int


class AdminProfileDetailResponse(BaseModel):
    profile: ProfileResponse | None = None
    statistics: StatisticsResponse


class AdminProfileBatchRequest(BaseModel):
    user_ids: list[UUID] = Field(default_factory=list, max_length=200)
