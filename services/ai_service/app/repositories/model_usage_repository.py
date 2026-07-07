"""Model usage repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_usage import ModelUsage
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class ModelUsageRepository:
    """Repository for :class:`ModelUsage` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_usage(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        latency_ms: int,
        estimated_cost: float,
    ) -> ModelUsage:
        usage = ModelUsage(
            session_id=session_id,
            user_id=user_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost=estimated_cost,
        )
        try:
            self._db.add(usage)
            self._db.commit()
            self._db.refresh(usage)
            return usage
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to create model usage: %s", exc)
            raise RepositoryError("Failed to record model usage.") from exc

    def list_by_session(self, session_id: UUID) -> list[ModelUsage]:
        stmt = (
            select(ModelUsage)
            .where(ModelUsage.session_id == session_id)
            .order_by(ModelUsage.created_at)
        )
        return list(self._db.scalars(stmt).all())
