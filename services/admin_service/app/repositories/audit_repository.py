"""Audit log repository (append-only)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.audit_log import AdminAuditLog
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AuditRepository:
    """Persist and query admin audit logs. Deletion is intentionally unsupported."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        admin_id: UUID,
        action: str,
        target_user_id: UUID | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> AdminAuditLog:
        row = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            reason=reason,
            metadata_=metadata,
        )
        try:
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
            return row
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to write audit log: %s", exc)
            raise RepositoryError("Failed to write audit log.") from exc

    def list_logs(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        admin_id: UUID | None = None,
        target_user_id: UUID | None = None,
        action: str | None = None,
    ) -> tuple[list[AdminAuditLog], int]:
        from sqlalchemy import func

        try:
            stmt = select(AdminAuditLog)
            count_stmt = select(func.count()).select_from(AdminAuditLog)
            if admin_id is not None:
                stmt = stmt.where(AdminAuditLog.admin_id == admin_id)
                count_stmt = count_stmt.where(AdminAuditLog.admin_id == admin_id)
            if target_user_id is not None:
                stmt = stmt.where(AdminAuditLog.target_user_id == target_user_id)
                count_stmt = count_stmt.where(
                    AdminAuditLog.target_user_id == target_user_id
                )
            if action is not None:
                stmt = stmt.where(AdminAuditLog.action == action)
                count_stmt = count_stmt.where(AdminAuditLog.action == action)

            total = int(self._db.scalar(count_stmt) or 0)
            rows = list(
                self._db.scalars(
                    stmt.order_by(AdminAuditLog.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                ).all()
            )
            return rows, total
        except SQLAlchemyError as exc:
            logger.error("Failed to list audit logs: %s", exc)
            raise RepositoryError("Failed to list audit logs.") from exc
