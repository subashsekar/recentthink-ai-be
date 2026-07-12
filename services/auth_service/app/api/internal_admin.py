"""Internal admin HTTP routes for Auth Service identity operations.

Consumed exclusively by the Admin Service via ``X-Internal-Service-Token``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.database import get_db
from app.dependencies.internal import require_internal_service
from app.dependencies.repositories import (
    get_refresh_token_repository,
    get_user_repository,
)
from app.models.enums import Role
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.admin_users import (
    AdminBlockUserRequest,
    AdminDashboardIdentityStats,
    AdminMutationResponse,
    AdminReasonRequest,
    AdminUserIdsResponse,
    AdminUserListResponse,
    AdminUserResponse,
)
from app.services.admin_user_management_service import AdminUserManagementService
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def get_admin_user_management_service(
    db: Session = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
    refresh_token_repository: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
) -> AdminUserManagementService:
    return AdminUserManagementService(
        db=db,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
    )


def _actor_id(
    x_admin_actor_id: Annotated[str | None, Header(alias="X-Admin-Actor-Id")] = None,
) -> UUID:
    if not x_admin_actor_id:
        # Service token already validated; fall back is only for read paths.
        return UUID("00000000-0000-0000-0000-000000000000")
    return UUID(x_admin_actor_id)


@router.get(
    "/dashboard-stats",
    response_model=AdminDashboardIdentityStats,
    dependencies=[Depends(require_internal_service)],
)
def dashboard_stats(
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminDashboardIdentityStats:
    return service.get_dashboard_stats()


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    dependencies=[Depends(require_internal_service)],
)
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: str | None = None,
    email: str | None = None,
    role: Role | None = None,
    is_verified: bool | None = None,
    is_blocked: bool | None = None,
    is_active: bool | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = Query("created_at"),
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminUserListResponse:
    return service.list_users(
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
    )


@router.get(
    "/users/ids",
    response_model=AdminUserIdsResponse,
    dependencies=[Depends(require_internal_service)],
)
def list_user_ids(
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminUserIdsResponse:
    return service.list_user_ids()


@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    dependencies=[Depends(require_internal_service)],
)
def get_user(
    user_id: UUID,
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminUserResponse:
    return service.get_user(user_id)


@router.patch(
    "/users/{user_id}/block",
    response_model=AdminMutationResponse,
    dependencies=[Depends(require_internal_service)],
)
def block_user(
    user_id: UUID,
    payload: AdminBlockUserRequest,
    actor_id: UUID = Depends(_actor_id),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminMutationResponse:
    return service.block_user(user_id, actor_id=actor_id, reason=payload.reason)


@router.patch(
    "/users/{user_id}/unblock",
    response_model=AdminMutationResponse,
    dependencies=[Depends(require_internal_service)],
)
def unblock_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    actor_id: UUID = Depends(_actor_id),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminMutationResponse:
    return service.unblock_user(user_id, actor_id=actor_id, reason=payload.reason)


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=AdminMutationResponse,
    dependencies=[Depends(require_internal_service)],
)
def deactivate_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    actor_id: UUID = Depends(_actor_id),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminMutationResponse:
    return service.deactivate_user(user_id, actor_id=actor_id, reason=payload.reason)


@router.patch(
    "/users/{user_id}/activate",
    response_model=AdminMutationResponse,
    dependencies=[Depends(require_internal_service)],
)
def activate_user(
    user_id: UUID,
    payload: AdminReasonRequest,
    actor_id: UUID = Depends(_actor_id),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> AdminMutationResponse:
    return service.activate_user(user_id, actor_id=actor_id, reason=payload.reason)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_internal_service)],
)
def delete_user(
    user_id: UUID,
    reason: str | None = Query(default=None, max_length=500),
    actor_id: UUID = Depends(_actor_id),
    service: AdminUserManagementService = Depends(get_admin_user_management_service),
) -> None:
    service.delete_user(user_id, actor_id=actor_id, reason=reason)
