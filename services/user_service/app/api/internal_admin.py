"""Internal admin HTTP routes for User Service profile data."""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.internal import require_internal_service
from app.dependencies.repositories import (
    get_profile_repository,
    get_statistics_repository,
)
from app.models.enums import CurrentStatus, PrimarySkill
from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository
from app.schemas.admin_internal import (
    AdminDashboardProfileStats,
    AdminProfileBatchRequest,
    AdminProfileDetailResponse,
    AdminProfileListItem,
    AdminProfileListResponse,
)
from app.schemas.profile import ProfileResponse, StatisticsResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


@router.get(
    "/dashboard-stats",
    response_model=AdminDashboardProfileStats,
    dependencies=[Depends(require_internal_service)],
)
def dashboard_stats(
    profiles: ProfileRepository = Depends(get_profile_repository),
) -> AdminDashboardProfileStats:
    counts = profiles.dashboard_status_counts()
    return AdminDashboardProfileStats(**counts)


@router.get(
    "/profiles",
    response_model=AdminProfileListResponse,
    dependencies=[Depends(require_internal_service)],
)
def list_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    primary_skill: PrimarySkill | None = None,
    current_status: CurrentStatus | None = None,
    name: str | None = None,
    profiles: ProfileRepository = Depends(get_profile_repository),
) -> AdminProfileListResponse:
    skip = (page - 1) * page_size
    items, total = profiles.list_profiles(
        skip=skip,
        limit=page_size,
        primary_skill=primary_skill,
        current_status=current_status,
        name=name,
    )
    return AdminProfileListResponse(
        items=[AdminProfileListItem.model_validate(p) for p in items],
        total=total,
    )


@router.post(
    "/profiles/batch",
    response_model=AdminProfileListResponse,
    dependencies=[Depends(require_internal_service)],
)
def batch_profiles(
    payload: AdminProfileBatchRequest,
    profiles: ProfileRepository = Depends(get_profile_repository),
) -> AdminProfileListResponse:
    items = profiles.list_by_user_ids(payload.user_ids)
    return AdminProfileListResponse(
        items=[AdminProfileListItem.model_validate(p) for p in items],
        total=len(items),
    )


@router.get(
    "/profiles/{user_id}",
    response_model=AdminProfileDetailResponse,
    dependencies=[Depends(require_internal_service)],
)
def get_profile_detail(
    user_id: UUID,
    profiles: ProfileRepository = Depends(get_profile_repository),
    statistics: StatisticsRepository = Depends(get_statistics_repository),
) -> AdminProfileDetailResponse:
    profile = profiles.get_by_user_id(user_id)
    stats = statistics.get_for_user(user_id)
    return AdminProfileDetailResponse(
        profile=ProfileResponse.model_validate(profile) if profile else None,
        statistics=StatisticsResponse(
            problems_solved=stats.problems_solved,
            courses_completed=stats.courses_completed,
            patterns_learned=stats.patterns_learned,
            current_streak=stats.current_streak,
            longest_streak=stats.longest_streak,
            learning_hours=stats.learning_hours,
            last_active=stats.last_active,
        ),
    )
