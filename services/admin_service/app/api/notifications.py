"""User-facing notification polling APIs."""

from __future__ import annotations

from uuid import UUID

from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_notification_service
from app.schemas.admin import (
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
)
from app.services.notification_service import NotificationService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return service.list_for_user(
        current_user.user_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
    )


@router.patch("/read-all", response_model=MarkAllReadResponse)
def mark_all_read(
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_notification_service),
) -> MarkAllReadResponse:
    return service.mark_all_read(current_user.user_id)


@router.patch("/{notification_id}/read", response_model=NotificationItem)
def mark_read(
    notification_id: UUID,
    current_user: AuthenticatedUser = Depends(require_authenticated_user),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationItem:
    return service.mark_read(notification_id, current_user.user_id)
