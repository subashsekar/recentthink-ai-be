"""Usage analytics repository for Admin Service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.usage_record import UsageRecord
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class UsageAnalyticsRepository:
    """Read aggregates from ``usage_records``."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def platform_analytics(self) -> dict[str, object]:
        try:
            now = datetime.now(tz=UTC)
            day_ago = now - timedelta(days=1)
            month_ago = now - timedelta(days=30)

            total_requests = int(
                self._db.scalar(
                    select(func.coalesce(func.sum(UsageRecord.request_count), 0))
                )
                or 0
            )
            daily_requests = int(
                self._db.scalar(
                    select(func.coalesce(func.sum(UsageRecord.request_count), 0)).where(
                        UsageRecord.created_at >= day_ago
                    )
                )
                or 0
            )
            monthly_requests = int(
                self._db.scalar(
                    select(func.coalesce(func.sum(UsageRecord.request_count), 0)).where(
                        UsageRecord.created_at >= month_ago
                    )
                )
                or 0
            )
            token_usage = int(
                self._db.scalar(
                    select(func.coalesce(func.sum(UsageRecord.token_usage), 0))
                )
                or 0
            )

            top_features = self._db.execute(
                select(
                    UsageRecord.feature,
                    func.coalesce(func.sum(UsageRecord.request_count), 0),
                )
                .group_by(UsageRecord.feature)
                .order_by(func.sum(UsageRecord.request_count).desc())
                .limit(10)
            ).all()

            return {
                "total_requests": total_requests,
                "daily_requests": daily_requests,
                "monthly_requests": monthly_requests,
                "token_usage": token_usage,
                "top_features": [
                    {"feature": row[0], "requests": int(row[1])} for row in top_features
                ],
            }
        except Exception as exc:
            logger.error("Failed to load usage analytics: %s", exc)
            raise RepositoryError("Failed to load usage analytics.") from exc

    def user_usage(self, user_id: UUID, *, limit: int = 50) -> list[dict[str, object]]:
        try:
            rows = list(
                self._db.scalars(
                    select(UsageRecord)
                    .where(UsageRecord.user_id == user_id)
                    .order_by(UsageRecord.created_at.desc())
                    .limit(limit)
                ).all()
            )
            return [
                {
                    "id": str(r.id),
                    "feature": r.feature,
                    "service_name": r.service_name,
                    "request_count": r.request_count,
                    "token_usage": r.token_usage,
                    "execution_time_ms": r.execution_time_ms,
                    "session_id": str(r.session_id) if r.session_id else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("Failed to load usage for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to load user usage.") from exc
