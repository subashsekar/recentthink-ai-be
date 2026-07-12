"""Admin analytics aggregation from AI-owned tables."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.course import Course
from app.models.enums import AIFeature
from app.models.model_usage import ModelUsage
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AdminAnalyticsRepository:
    """Read-only aggregates for Admin Service HTTP APIs."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def platform_analytics(self) -> dict[str, float | int]:
        try:
            total_sessions = int(
                self._db.scalar(select(func.count()).select_from(AISession)) or 0
            )
            leetcode = int(
                self._db.scalar(
                    select(func.count())
                    .select_from(AISession)
                    .where(AISession.feature == AIFeature.LEETCODE)
                )
                or 0
            )
            hackerrank = int(
                self._db.scalar(
                    select(func.count())
                    .select_from(AISession)
                    .where(AISession.feature == AIFeature.HACKERRANK)
                )
                or 0
            )
            dsa = int(
                self._db.scalar(
                    select(func.count())
                    .select_from(AISession)
                    .where(
                        AISession.feature.in_(
                            [AIFeature.DSA, AIFeature.DSA_PATTERN]
                        )
                    )
                )
                or 0
            )
            courses = int(
                self._db.scalar(select(func.count()).select_from(Course)) or 0
            )
            conversations = int(
                self._db.scalar(select(func.count()).select_from(AIMessage)) or 0
            )

            usage_row = self._db.execute(
                select(
                    func.coalesce(func.avg(ModelUsage.latency_ms), 0),
                    func.coalesce(func.avg(ModelUsage.total_tokens), 0),
                    func.coalesce(func.avg(ModelUsage.estimated_cost), 0),
                )
            ).one()

            return {
                "total_ai_sessions": total_sessions,
                "leetcode_sessions": leetcode,
                "hackerrank_sessions": hackerrank,
                "dsa_sessions": dsa,
                "courses_generated": courses,
                "total_conversations": conversations,
                "average_response_time": float(usage_row[0] or 0),
                "average_tokens": float(usage_row[1] or 0),
                "average_cost": float(usage_row[2] or 0),
            }
        except Exception as exc:
            logger.error("Failed to load AI platform analytics: %s", exc)
            raise RepositoryError("Failed to load AI analytics.") from exc

    def model_usage_breakdown(self) -> dict[str, object]:
        try:
            by_provider = self._db.execute(
                select(
                    ModelUsage.provider,
                    func.count(),
                    func.coalesce(func.sum(ModelUsage.total_tokens), 0),
                    func.coalesce(func.sum(ModelUsage.estimated_cost), 0),
                ).group_by(ModelUsage.provider)
            ).all()
            by_model = self._db.execute(
                select(
                    ModelUsage.model,
                    func.count(),
                    func.coalesce(func.sum(ModelUsage.total_tokens), 0),
                    func.coalesce(func.sum(ModelUsage.estimated_cost), 0),
                ).group_by(ModelUsage.model)
            ).all()
            return {
                "provider_usage": [
                    {
                        "provider": row[0],
                        "requests": int(row[1]),
                        "tokens": int(row[2]),
                        "estimated_cost": float(row[3]),
                    }
                    for row in by_provider
                ],
                "model_usage": [
                    {
                        "model": row[0],
                        "requests": int(row[1]),
                        "tokens": int(row[2]),
                        "estimated_cost": float(row[3]),
                    }
                    for row in by_model
                ],
            }
        except Exception as exc:
            logger.error("Failed to load model usage breakdown: %s", exc)
            raise RepositoryError("Failed to load model usage.") from exc

    def user_history(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        try:
            sessions = list(
                self._db.scalars(
                    select(AISession)
                    .where(AISession.user_id == user_id)
                    .order_by(AISession.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                ).all()
            )
            usages = list(
                self._db.scalars(
                    select(ModelUsage)
                    .where(ModelUsage.user_id == user_id)
                    .order_by(ModelUsage.created_at.desc())
                    .limit(limit)
                ).all()
            )
            return {
                "sessions": [
                    {
                        "id": str(s.id),
                        "feature": s.feature.value if hasattr(s.feature, "value") else str(s.feature),
                        "title": s.title,
                        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                        "created_at": s.created_at.isoformat() if s.created_at else None,
                    }
                    for s in sessions
                ],
                "usage": [
                    {
                        "id": str(u.id),
                        "session_id": str(u.session_id),
                        "model": u.model,
                        "provider": u.provider,
                        "total_tokens": u.total_tokens,
                        "latency_ms": u.latency_ms,
                        "estimated_cost": u.estimated_cost,
                        "created_at": u.created_at.isoformat() if u.created_at else None,
                    }
                    for u in usages
                ],
            }
        except Exception as exc:
            logger.error("Failed to load AI history for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to load AI history.") from exc
