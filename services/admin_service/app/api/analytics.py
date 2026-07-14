"""Admin AI Usage Analytics HTTP routes (aggregated from Usage Service)."""

from __future__ import annotations

from uuid import UUID

from app.dependencies.auth import AuthenticatedUser, require_admin_user
from app.dependencies.services import get_analytics_service
from app.schemas.admin import (
    AnalyticsDashboardResponse,
    ChartsResponse,
    CostAnalyticsResponse,
    FeatureAnalyticsResponse,
    ModelAnalyticsListResponse,
    ProviderAnalyticsResponse,
    TokenAnalyticsResponse,
    UserUsageDetailAdminResponse,
    UserUsageTableResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.report_export import build_export_file
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"])


@router.get("/dashboard", response_model=AnalyticsDashboardResponse)
async def analytics_dashboard(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsDashboardResponse:
    return await service.get_dashboard()


@router.get("/tokens", response_model=TokenAnalyticsResponse)
async def analytics_tokens(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> TokenAnalyticsResponse:
    return await service.get_tokens()


@router.get("/models", response_model=ModelAnalyticsListResponse)
async def analytics_models(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ModelAnalyticsListResponse:
    return await service.get_models()


@router.get("/providers", response_model=ProviderAnalyticsResponse)
async def analytics_providers(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ProviderAnalyticsResponse:
    return await service.get_providers()


@router.get("/features", response_model=FeatureAnalyticsResponse)
async def analytics_features(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> FeatureAnalyticsResponse:
    return await service.get_features()


@router.get("/users", response_model=UserUsageTableResponse)
async def analytics_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("total_tokens"),
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    search: str | None = None,
    role: str | None = None,
    current_status: str | None = None,
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> UserUsageTableResponse:
    return await service.get_users_table(
        page=page,
        page_size=page_size,
        sort=sort,
        order=order,
        search=search,
        role=role,
        current_status=current_status,
    )


@router.get("/users/{user_id}", response_model=UserUsageDetailAdminResponse)
async def analytics_user_detail(
    user_id: UUID,
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> UserUsageDetailAdminResponse:
    return await service.get_user_detail(user_id)


@router.get("/charts", response_model=ChartsResponse)
async def analytics_charts(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ChartsResponse:
    return await service.get_charts()


@router.get("/costs", response_model=CostAnalyticsResponse)
async def analytics_costs(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> CostAnalyticsResponse:
    return await service.get_costs()


@router.get("/export")
async def analytics_export(
    report: str = Query(
        ...,
        pattern=(
            "^(?i)(user_usage|feature_usage|model_usage|"
            "provider_usage|token_usage|cost_analysis)$"
        ),
    ),
    format: str = Query(
        "csv",
        pattern="^(?i)(csv|excel|xlsx|pdf)$",
        alias="format",
    ),
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> Response:
    payload = await service.export_payload(report)
    try:
        content, media_type, filename = build_export_file(
            report=str(payload.get("report", report)),
            columns=list(payload.get("columns", [])),
            rows=list(payload.get("rows", [])),
            fmt=format,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
