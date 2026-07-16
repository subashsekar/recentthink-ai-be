"""AI session data-access repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, desc, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.ai_session import AISession
from app.models.enums import AIFeature, SessionStatus
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AISessionRepository:
    """Repository for :class:`AISession` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_session(
        self,
        *,
        user_id: UUID,
        feature: AIFeature,
        title: str | None = None,
        status: SessionStatus = SessionStatus.PENDING,
        context_metadata: dict | None = None,
    ) -> AISession:
        session = AISession(
            user_id=user_id,
            feature=feature,
            title=title,
            status=status,
            context_metadata=context_metadata,
        )
        try:
            self._db.add(session)
            self._db.commit()
            self._db.refresh(session)
            return session
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to create AI session: %s", exc)
            raise RepositoryError("Failed to create session.") from exc

    def get_by_id(self, session_id: UUID) -> AISession | None:
        return self._db.get(AISession, session_id)

    def get_by_id_with_relations(self, session_id: UUID) -> AISession | None:
        stmt = (
            select(AISession)
            .options(
                joinedload(AISession.messages),
                joinedload(AISession.executions),
                joinedload(AISession.memory),
                joinedload(AISession.model_usages),
            )
            .where(AISession.id == session_id)
        )
        return self._db.scalars(stmt).unique().first()

    def list_by_user(
        self,
        user_id: UUID,
        *,
        feature: AIFeature | None = None,
        search: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AISession]:
        stmt = select(AISession).where(AISession.user_id == user_id)
        if feature is not None:
            stmt = stmt.where(AISession.feature == feature)
        if not include_archived:
            stmt = stmt.where(AISession.is_archived.is_(False))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    AISession.title.ilike(pattern),
                    AISession.summary.ilike(pattern),
                ),
            )
        stmt = (
            stmt.order_by(
                desc(AISession.is_pinned),
                desc(AISession.last_active_at),
                desc(AISession.updated_at),
                desc(AISession.created_at),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def list_all(
        self,
        *,
        feature: AIFeature | None = None,
        search: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AISession]:
        stmt = select(AISession)
        if feature is not None:
            stmt = stmt.where(AISession.feature == feature)
        if not include_archived:
            stmt = stmt.where(AISession.is_archived.is_(False))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    AISession.title.ilike(pattern),
                    AISession.summary.ilike(pattern),
                ),
            )
        stmt = (
            stmt.order_by(
                desc(AISession.is_pinned),
                desc(AISession.last_active_at),
                desc(AISession.updated_at),
                desc(AISession.created_at),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def count_by_user(
        self,
        user_id: UUID,
        *,
        feature: AIFeature | None = None,
        include_archived: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(AISession).where(AISession.user_id == user_id)
        if feature is not None:
            stmt = stmt.where(AISession.feature == feature)
        if not include_archived:
            stmt = stmt.where(AISession.is_archived.is_(False))
        return int(self._db.scalar(stmt) or 0)

    def touch_last_active(self, session_id: UUID) -> None:
        self.update_session(session_id, last_active_at=datetime.now(UTC))

    def update_session(self, session_id: UUID, **fields: object) -> AISession:
        session = self.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        for key, value in fields.items():
            setattr(session, key, value)
        try:
            self._db.commit()
            self._db.refresh(session)
            return session
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update session.") from exc

    def delete_session(self, session_id: UUID) -> None:
        session = self.get_by_id(session_id)
        if session is None:
            raise RecordNotFoundError(f"Session '{session_id}' not found.")
        try:
            self._db.delete(session)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to delete session.") from exc

    def delete_by_user(self, user_id: UUID, *, commit: bool = True) -> int:
        """Delete all sessions for a user (DB cascades messages and linked rows)."""
        try:
            result = self._db.execute(delete(AISession).where(AISession.user_id == user_id))
            if commit:
                self._db.commit()
            return int(result.rowcount or 0)
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to delete AI sessions for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to delete user sessions.") from exc
