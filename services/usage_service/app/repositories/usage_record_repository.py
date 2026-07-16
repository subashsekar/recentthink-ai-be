"""Usage metering data-access repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.usage_record import UsageRecord
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class UsageRecordRepository:
    """Repository for :class:`UsageRecord` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_record(
        self,
        *,
        user_id: UUID,
        service_name: str,
        feature: str,
        request_count: int,
        token_usage: int,
        execution_time_ms: int,
        session_id: UUID | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        model: str | None = None,
        provider: str | None = None,
        estimated_cost: float = 0.0,
        success: bool = True,
        section_tokens: dict | None = None,
    ) -> UsageRecord:
        record = UsageRecord(
            user_id=user_id,
            service_name=service_name,
            feature=feature,
            request_count=request_count,
            token_usage=token_usage,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            execution_time_ms=execution_time_ms,
            model=model,
            provider=provider,
            estimated_cost=estimated_cost,
            success=success,
            session_id=session_id,
            section_tokens=section_tokens,
        )
        try:
            self._db.add(record)
            self._db.commit()
            self._db.refresh(record)
            return record
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to create usage record: %s", exc)
            raise RepositoryError("Failed to record usage.") from exc

    def delete_by_user(self, user_id: UUID) -> int:
        """Delete all usage records for a user. Idempotent."""
        try:
            result = self._db.execute(
                delete(UsageRecord).where(UsageRecord.user_id == user_id),
            )
            self._db.commit()
            deleted = int(result.rowcount or 0)
            logger.info("Deleted %s usage records for user_id=%s", deleted, user_id)
            return deleted
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to delete usage for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to delete user usage records.") from exc
