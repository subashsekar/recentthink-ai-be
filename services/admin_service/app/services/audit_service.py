"""Audit service."""

from __future__ import annotations

from uuid import UUID

from app.models.audit_log import AdminAuditLog
from app.repositories.audit_repository import AuditRepository
from app.schemas.admin import AuditListResponse, AuditLogItem


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self._repo = repository

    def log(
        self,
        *,
        admin_id: UUID,
        action: str,
        target_user_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> AdminAuditLog:
        return self._repo.create(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            reason=reason,
            metadata=metadata,
        )

    def list_logs(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        admin_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
    ) -> AuditListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        rows, total = self._repo.list_logs(
            skip=skip,
            limit=page_size,
            admin_id=admin_id,
            target_user_id=target_user_id,
            action=action,
        )
        return AuditListResponse(
            items=[
                AuditLogItem(
                    id=r.id,
                    admin_id=r.admin_id,
                    action=r.action,
                    target_user_id=r.target_user_id,
                    reason=r.reason,
                    created_at=r.created_at,
                )
                for r in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
