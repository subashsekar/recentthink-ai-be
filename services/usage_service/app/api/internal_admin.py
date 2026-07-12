"""Internal admin HTTP routes for Usage Service analytics."""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.auth import require_internal_service
from app.repositories.usage_analytics_repository import UsageAnalyticsRepository
from app.schemas.admin_internal import UsageAnalyticsResponse, UserUsageResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def get_usage_analytics_repository(
    db: Session = Depends(get_db),
) -> UsageAnalyticsRepository:
    return UsageAnalyticsRepository(db)


@router.get(
    "/analytics",
    response_model=UsageAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> UsageAnalyticsResponse:
    data = repo.platform_analytics()
    return UsageAnalyticsResponse(**data)


@router.get(
    "/users/{user_id}",
    response_model=UserUsageResponse,
    dependencies=[Depends(require_internal_service)],
)
def user_usage(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> UserUsageResponse:
    return UserUsageResponse(items=repo.user_usage(user_id, limit=limit))
