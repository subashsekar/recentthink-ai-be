"""Notification repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.notification import Notification
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        type: str,
    ) -> Notification:
        row = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
        )
        try:
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
            return row
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to create notification: %s", exc)
            raise RepositoryError("Failed to create notification.") from exc

    def create_many(
        self,
        *,
        user_ids: list[UUID],
        title: str,
        message: str,
        type: str,
    ) -> int:
        rows = [
            Notification(user_id=uid, title=title, message=message, type=type)
            for uid in user_ids
        ]
        try:
            self._db.add_all(rows)
            self._db.commit()
            return len(rows)
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to create notifications: %s", exc)
            raise RepositoryError("Failed to create notifications.") from exc

    def list_for_user(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        try:
            stmt = select(Notification).where(Notification.user_id == user_id)
            count_stmt = (
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id)
            )
            if unread_only:
                stmt = stmt.where(Notification.is_read.is_(False))
                count_stmt = count_stmt.where(Notification.is_read.is_(False))
            total = int(self._db.scalar(count_stmt) or 0)
            rows = list(
                self._db.scalars(
                    stmt.order_by(Notification.created_at.desc())
                    .offset(skip)
                    .limit(limit)
                ).all()
            )
            return rows, total
        except SQLAlchemyError as exc:
            logger.error("Failed to list notifications: %s", exc)
            raise RepositoryError("Failed to list notifications.") from exc

    def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        row = self._db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        if row is None:
            raise RecordNotFoundError("Notification not found.")
        row.is_read = True
        try:
            self._db.commit()
            self._db.refresh(row)
            return row
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise RepositoryError("Failed to mark notification read.") from exc

    def mark_all_read(self, user_id: UUID) -> int:
        try:
            result = self._db.execute(
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                )
                .values(is_read=True)
            )
            self._db.commit()
            return int(result.rowcount or 0)
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise RepositoryError("Failed to mark notifications read.") from exc
