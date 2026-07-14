"""Internal admin HTTP routes for Usage Service analytics."""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.auth import require_internal_service
from app.repositories.usage_analytics_repository import UsageAnalyticsRepository
from app.schemas.admin_internal import (
    AnalyticsDashboardResponse,
    BatchUserStatsResponse,
    ChartsResponse,
    CostAnalyticsResponse,
    ExportPayloadResponse,
    FeatureAnalyticsListResponse,
    ModelAnalyticsListResponse,
    ProviderAnalyticsListResponse,
    TokenAnalyticsResponse,
    UsageAnalyticsResponse,
    UserUsageDetailResponse,
    UserUsageListResponse,
    UserUsageResponse,
)
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
    "/analytics/dashboard",
    response_model=AnalyticsDashboardResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_dashboard(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> AnalyticsDashboardResponse:
    return AnalyticsDashboardResponse(**repo.analytics_dashboard())


@router.get(
    "/analytics/tokens",
    response_model=TokenAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_tokens(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> TokenAnalyticsResponse:
    return TokenAnalyticsResponse(**repo.token_analytics())


@router.get(
    "/analytics/models",
    response_model=ModelAnalyticsListResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_models(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> ModelAnalyticsListResponse:
    return ModelAnalyticsListResponse(**repo.model_analytics())


@router.get(
    "/analytics/providers",
    response_model=ProviderAnalyticsListResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_providers(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> ProviderAnalyticsListResponse:
    return ProviderAnalyticsListResponse(**repo.provider_analytics())


@router.get(
    "/analytics/features",
    response_model=FeatureAnalyticsListResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_features(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> FeatureAnalyticsListResponse:
    return FeatureAnalyticsListResponse(**repo.feature_analytics())


@router.get(
    "/analytics/users",
    response_model=UserUsageListResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("total_tokens"),
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    user_ids: list[UUID] | None = Query(default=None),
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> UserUsageListResponse:
    return UserUsageListResponse(
        **repo.users_analytics(
            page=page,
            page_size=page_size,
            sort=sort,
            order=order,
            user_ids=user_ids,
        )
    )


@router.get(
    "/analytics/users/{user_id}",
    response_model=UserUsageDetailResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_user_detail(
    user_id: UUID,
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> UserUsageDetailResponse:
    return UserUsageDetailResponse(**repo.user_detail(user_id))


@router.get(
    "/analytics/charts",
    response_model=ChartsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_charts(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> ChartsResponse:
    return ChartsResponse(**repo.charts())


@router.get(
    "/analytics/costs",
    response_model=CostAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_costs(
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> CostAnalyticsResponse:
    return CostAnalyticsResponse(**repo.cost_analytics())


@router.get(
    "/analytics/export",
    response_model=ExportPayloadResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics_export(
    report: str = Query(
        ...,
        pattern=(
            "^(?i)(user_usage|feature_usage|model_usage|"
            "provider_usage|token_usage|cost_analysis)$"
        ),
    ),
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> ExportPayloadResponse:
    return ExportPayloadResponse(**repo.export_payload(report))


@router.get(
    "/users/stats",
    response_model=BatchUserStatsResponse,
    dependencies=[Depends(require_internal_service)],
)
def batch_user_stats(
    user_ids: list[UUID] = Query(...),
    repo: UsageAnalyticsRepository = Depends(get_usage_analytics_repository),
) -> BatchUserStatsResponse:
    return BatchUserStatsResponse(**repo.batch_user_stats(user_ids))


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
