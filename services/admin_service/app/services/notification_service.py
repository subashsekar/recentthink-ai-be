"""Notification service (polling-based)."""

from __future__ import annotations

from uuid import UUID

from app.clients.auth_client import AuthServiceClient
from app.models.enums import AuditAction, NotificationType
from app.repositories.notification_repository import NotificationRepository
from app.schemas.admin import (
    BroadcastNotificationRequest,
    BroadcastNotificationResponse,
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
)
from app.services.audit_service import AuditService


class NotificationService:
    def __init__(
        self,
        *,
        repository: NotificationRepository,
        auth_client: AuthServiceClient,
        audit_service: AuditService,
    ) -> None:
        self._repo = repository
        self._auth = auth_client
        self._audit = audit_service

    def list_for_user(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        unread_only: bool = False,
    ) -> NotificationListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        rows, total = self._repo.list_for_user(
            user_id,
            skip=skip,
            limit=page_size,
            unread_only=unread_only,
        )
        return NotificationListResponse(
            items=[NotificationItem.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def mark_read(self, notification_id: UUID, user_id: UUID) -> NotificationItem:
        row = self._repo.mark_read(notification_id, user_id)
        return NotificationItem.model_validate(row)

    def mark_all_read(self, user_id: UUID) -> MarkAllReadResponse:
        updated = self._repo.mark_all_read(user_id)
        return MarkAllReadResponse(
            message="All notifications marked as read.",
            updated=updated,
        )

    async def broadcast(
        self,
        payload: BroadcastNotificationRequest,
        *,
        actor_id: UUID,
    ) -> BroadcastNotificationResponse:
        user_ids = await self._auth.list_user_ids()
        created = self._repo.create_many(
            user_ids=user_ids,
            title=payload.title,
            message=payload.message,
            type=payload.type or NotificationType.ANNOUNCEMENT.value,
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.ANNOUNCEMENT_SENT.value,
            reason=payload.title,
            metadata={"created": created, "type": payload.type},
        )
        return BroadcastNotificationResponse(
            message="Broadcast sent.",
            created=created,
        )
