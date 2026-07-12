"""Admin management HTTP routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.dependencies.auth import AuthenticatedUser, require_admin_user
from app.dependencies.services import (
    get_analytics_service,
    get_audit_service,
    get_dashboard_service,
    get_notification_service,
    get_system_health_service,
    get_user_management_service,
)
from app.schemas.admin import (
    AnalyticsResponse,
    AuditListResponse,
    BroadcastNotificationRequest,
    BroadcastNotificationResponse,
    DashboardResponse,
    HealthResponse,
    ModelAnalyticsResponse,
    MutationResponse,
    ReasonRequest,
    UsageAnalyticsResponse,
    UserDetailResponse,
    UserListResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.services.system_health_service import SystemHealthService
from app.services.user_management_service import UserManagementService
from fastapi import APIRouter, Depends, Query, status

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await service.get_dashboard()


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = None,
    email: str | None = None,
    role: str | None = None,
    is_verified: bool | None = None,
    is_blocked: bool | None = None,
    is_active: bool | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "created_at",
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    primary_skill: str | None = None,
    current_status: str | None = None,
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> UserListResponse:
    return await service.list_users(
        page=page,
        page_size=page_size,
        name=name,
        email=email,
        role=role,
        is_verified=is_verified,
        is_blocked=is_blocked,
        is_active=is_active,
        created_from=created_from,
        created_to=created_to,
        sort=sort,
        order=order,
        primary_skill=primary_skill,
        current_status=current_status,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user(
    user_id: UUID,
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> UserDetailResponse:
    return await service.get_user(user_id)


@router.patch("/users/{user_id}/block", response_model=MutationResponse)
async def block_user(
    user_id: UUID,
    payload: ReasonRequest,
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> MutationResponse:
    return await service.block_user(
        user_id, actor_id=admin.user_id, reason=payload.reason
    )


@router.patch("/users/{user_id}/unblock", response_model=MutationResponse)
async def unblock_user(
    user_id: UUID,
    payload: ReasonRequest,
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> MutationResponse:
    return await service.unblock_user(
        user_id, actor_id=admin.user_id, reason=payload.reason
    )


@router.patch("/users/{user_id}/activate", response_model=MutationResponse)
async def activate_user(
    user_id: UUID,
    payload: ReasonRequest,
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> MutationResponse:
    return await service.activate_user(
        user_id, actor_id=admin.user_id, reason=payload.reason
    )


@router.patch("/users/{user_id}/deactivate", response_model=MutationResponse)
async def deactivate_user(
    user_id: UUID,
    payload: ReasonRequest,
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> MutationResponse:
    return await service.deactivate_user(
        user_id, actor_id=admin.user_id, reason=payload.reason
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    reason: str | None = Query(default=None, max_length=500),
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: UserManagementService = Depends(get_user_management_service),
) -> None:
    await service.delete_user(user_id, actor_id=admin.user_id, reason=reason)


@router.get("/analytics", response_model=AnalyticsResponse)
async def analytics(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> AnalyticsResponse:
    return await service.get_ai_analytics()


@router.get("/usage", response_model=UsageAnalyticsResponse)
async def usage(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> UsageAnalyticsResponse:
    return await service.get_usage_analytics()


@router.get("/models", response_model=ModelAnalyticsResponse)
async def models(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AnalyticsService = Depends(get_analytics_service),
) -> ModelAnalyticsResponse:
    return await service.get_model_analytics()


@router.get("/audit-logs", response_model=AuditListResponse)
def audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_id: UUID | None = None,
    target_user_id: UUID | None = None,
    action: str | None = None,
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: AuditService = Depends(get_audit_service),
) -> AuditListResponse:
    return service.list_logs(
        page=page,
        page_size=page_size,
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
    )


@router.get("/system-health", response_model=HealthResponse)
async def system_health(
    _admin: AuthenticatedUser = Depends(require_admin_user),
    service: SystemHealthService = Depends(get_system_health_service),
) -> HealthResponse:
    return await service.get_health()


@router.post(
    "/notifications/broadcast",
    response_model=BroadcastNotificationResponse,
)
async def broadcast_notification(
    payload: BroadcastNotificationRequest,
    admin: AuthenticatedUser = Depends(require_admin_user),
    service: NotificationService = Depends(get_notification_service),
) -> BroadcastNotificationResponse:
    return await service.broadcast(payload, actor_id=admin.user_id)
