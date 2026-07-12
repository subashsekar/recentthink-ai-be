"""Internal admin HTTP routes for AI Service analytics."""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.internal import require_internal_service
from app.repositories.admin_analytics_repository import AdminAnalyticsRepository
from app.schemas.admin_internal import (
    AIAnalyticsResponse,
    AIUserHistoryResponse,
    ModelAnalyticsResponse,
)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def get_admin_analytics_repository(
    db: Session = Depends(get_db),
) -> AdminAnalyticsRepository:
    return AdminAnalyticsRepository(db)


@router.get(
    "/analytics",
    response_model=AIAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics(
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> AIAnalyticsResponse:
    return AIAnalyticsResponse(**repo.platform_analytics())


@router.get(
    "/models",
    response_model=ModelAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def models(
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> ModelAnalyticsResponse:
    return ModelAnalyticsResponse(**repo.model_usage_breakdown())


@router.get(
    "/users/{user_id}/history",
    response_model=AIUserHistoryResponse,
    dependencies=[Depends(require_internal_service)],
)
def user_history(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> AIUserHistoryResponse:
    return AIUserHistoryResponse(**repo.user_history(user_id, limit=limit, offset=offset))
