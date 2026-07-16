"""AI message data-access repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.ai_message import AIMessage
from app.models.enums import MessageRole, ModuleName
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AIMessageRepository:
    """Repository for :class:`AIMessage` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_message(
        self,
        *,
        session_id: UUID,
        role: MessageRole,
        content: str,
        module_name: ModuleName | None = None,
        content_metadata: dict | None = None,
    ) -> AIMessage:
        message = AIMessage(
            session_id=session_id,
            role=role,
            content=content,
            module_name=module_name,
            content_metadata=content_metadata,
        )
        try:
            self._db.add(message)
            self._db.commit()
            self._db.refresh(message)
            return message
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to create AI message: %s", exc)
            raise RepositoryError("Failed to create message.") from exc

    def get_by_id(self, message_id: UUID) -> AIMessage | None:
        return self._db.get(AIMessage, message_id)

    def update_message(self, message_id: UUID, **fields: object) -> AIMessage:
        message = self.get_by_id(message_id)
        if message is None:
            raise RecordNotFoundError(f"Message '{message_id}' not found.")
        for key, value in fields.items():
            setattr(message, key, value)
        try:
            self._db.commit()
            self._db.refresh(message)
            return message
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update message.") from exc

    def delete_message(self, message_id: UUID) -> None:
        message = self.get_by_id(message_id)
        if message is None:
            raise RecordNotFoundError(f"Message '{message_id}' not found.")
        try:
            self._db.delete(message)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to delete message.") from exc

    def get_preceding_user_message(
        self,
        session_id: UUID,
        *,
        before_created_at,
    ) -> AIMessage | None:
        stmt = (
            select(AIMessage)
            .where(
                AIMessage.session_id == session_id,
                AIMessage.role == MessageRole.USER,
                AIMessage.created_at < before_created_at,
            )
            .order_by(desc(AIMessage.created_at))
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def count_by_session(self, session_id: UUID) -> int:
        from sqlalchemy import func

        stmt = (
            select(func.count())
            .select_from(AIMessage)
            .where(AIMessage.session_id == session_id)
        )
        return int(self._db.scalar(stmt) or 0)

    def list_all_by_session(self, session_id: UUID) -> list[AIMessage]:
        stmt = (
            select(AIMessage)
            .where(AIMessage.session_id == session_id)
            .order_by(AIMessage.created_at)
        )
        return list(self._db.scalars(stmt).all())

    def list_by_session(
        self,
        session_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AIMessage]:
        stmt = (
            select(AIMessage)
            .where(AIMessage.session_id == session_id)
            .order_by(AIMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def search_by_content(
        self,
        session_id: UUID,
        query: str,
        *,
        limit: int = 50,
    ) -> list[AIMessage]:
        pattern = f"%{query}%"
        stmt = (
            select(AIMessage)
            .where(AIMessage.session_id == session_id, AIMessage.content.ilike(pattern))
            .order_by(desc(AIMessage.created_at))
            .limit(limit)
        )
        return list(self._db.scalars(stmt).all())
