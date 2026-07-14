"""Usage analytics repository for Admin Service (all aggregation lives here)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.usage_record import UsageRecord
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)

KNOWN_FEATURES = (
    "leetcode",
    "hackerrank",
    "course_generator",
    "dsa_pattern",
    "dsa",
    "interview",
)

SORTABLE_USER_COLUMNS = {
    "total_requests": "total_requests",
    "total_tokens": "total_tokens",
    "estimated_cost": "estimated_cost",
    "last_active": "last_active",
    "prompt_tokens": "prompt_tokens",
    "completion_tokens": "completion_tokens",
}


class UsageAnalyticsRepository:
    """Read aggregates from ``usage_records`` — single source of analytics truth."""

    def __init__(self, db: Session) -> None:
        self._db = db

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _now() -> datetime:
        return datetime.now(tz=UTC)

    @staticmethod
    def _start_of_day(now: datetime) -> datetime:
        return datetime(now.year, now.month, now.day, tzinfo=UTC)

    def _window_totals(self, since: datetime | None = None) -> dict[str, Any]:
        q = select(
            func.coalesce(func.sum(UsageRecord.request_count), 0),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.token_usage), 0),
            func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
            func.coalesce(func.count(func.distinct(UsageRecord.session_id)), 0),
            func.coalesce(func.avg(UsageRecord.execution_time_ms), 0.0),
            func.coalesce(func.count(func.distinct(UsageRecord.user_id)), 0),
        )
        if since is not None:
            q = q.where(UsageRecord.created_at >= since)
        row = self._db.execute(q).one()
        requests = int(row[0] or 0)
        tokens = int(row[3] or 0)
        cost = float(row[4] or 0.0)
        return {
            "requests": requests,
            "prompt_tokens": int(row[1] or 0),
            "completion_tokens": int(row[2] or 0),
            "tokens": tokens,
            "cost": cost,
            "sessions": int(row[5] or 0),
            "average_execution_time_ms": float(row[6] or 0.0),
            "active_users": int(row[7] or 0),
            "average_tokens_per_request": (tokens / requests) if requests else 0.0,
            "average_cost_per_request": (cost / requests) if requests else 0.0,
        }

    def _top_feature(self, *, since: datetime | None = None, limit: int = 1) -> str | None:
        q = (
            select(
                UsageRecord.feature,
                func.coalesce(func.sum(UsageRecord.request_count), 0).label("reqs"),
            )
            .group_by(UsageRecord.feature)
            .order_by(func.sum(UsageRecord.request_count).desc())
            .limit(limit)
        )
        if since is not None:
            q = q.where(UsageRecord.created_at >= since)
        row = self._db.execute(q).first()
        return str(row[0]) if row else None

    def _top_model(self) -> str | None:
        row = self._db.execute(
            select(
                UsageRecord.model,
                func.coalesce(func.sum(UsageRecord.request_count), 0),
            )
            .where(UsageRecord.model.is_not(None))
            .group_by(UsageRecord.model)
            .order_by(func.sum(UsageRecord.request_count).desc())
            .limit(1)
        ).first()
        return str(row[0]) if row and row[0] else None

    def _top_provider(self) -> str | None:
        row = self._db.execute(
            select(
                UsageRecord.provider,
                func.coalesce(func.sum(UsageRecord.request_count), 0),
            )
            .where(UsageRecord.provider.is_not(None))
            .group_by(UsageRecord.provider)
            .order_by(func.sum(UsageRecord.request_count).desc())
            .limit(1)
        ).first()
        return str(row[0]) if row and row[0] else None

    def _top_users(self, *, limit: int = 10) -> list[dict[str, Any]]:
        rows = self._db.execute(
            select(
                UsageRecord.user_id,
                func.coalesce(func.sum(UsageRecord.token_usage), 0),
                func.coalesce(func.sum(UsageRecord.request_count), 0),
                func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
            )
            .group_by(UsageRecord.user_id)
            .order_by(func.sum(UsageRecord.token_usage).desc())
            .limit(limit)
        ).all()
        return [
            {
                "user_id": row[0],
                "total_tokens": int(row[1]),
                "total_requests": int(row[2]),
                "estimated_cost": float(row[3]),
            }
            for row in rows
        ]

    def _feature_breakdown(
        self,
        *,
        user_id: UUID | None = None,
        since: datetime | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        q = select(
            UsageRecord.feature,
            func.coalesce(func.sum(UsageRecord.request_count), 0),
            func.coalesce(func.sum(UsageRecord.token_usage), 0),
            func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
            func.coalesce(func.avg(UsageRecord.execution_time_ms), 0.0),
        ).group_by(UsageRecord.feature)
        if user_id is not None:
            q = q.where(UsageRecord.user_id == user_id)
        if since is not None:
            q = q.where(UsageRecord.created_at >= since)
        q = q.order_by(func.sum(UsageRecord.request_count).desc())
        if limit is not None:
            q = q.limit(limit)
        rows = self._db.execute(q).all()
        items: list[dict[str, Any]] = []
        for row in rows:
            requests = int(row[1] or 0)
            tokens = int(row[2] or 0)
            cost = float(row[3] or 0.0)
            items.append(
                {
                    "feature": row[0],
                    "requests": requests,
                    "tokens": tokens,
                    "cost": cost,
                    "average_time_ms": float(row[4] or 0.0),
                    "average_tokens": (tokens / requests) if requests else 0.0,
                    "average_cost": (cost / requests) if requests else 0.0,
                }
            )
        return items

    def _model_breakdown(
        self,
        *,
        user_id: UUID | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        provider_agg = func.max(UsageRecord.provider)
        q = select(
            UsageRecord.model,
            provider_agg,
            func.coalesce(func.sum(UsageRecord.request_count), 0),
            func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
            func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
            func.coalesce(func.sum(UsageRecord.token_usage), 0),
            func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
            func.coalesce(func.avg(UsageRecord.execution_time_ms), 0.0),
            func.coalesce(
                func.avg(cast(case((UsageRecord.success.is_(True), 1), else_=0), Integer)),
                1.0,
            ),
        ).where(UsageRecord.model.is_not(None)).group_by(UsageRecord.model)
        if user_id is not None:
            q = q.where(UsageRecord.user_id == user_id)
        q = q.order_by(func.sum(UsageRecord.request_count).desc())
        if limit is not None:
            q = q.limit(limit)
        rows = self._db.execute(q).all()
        items: list[dict[str, Any]] = []
        for row in rows:
            success_rate = float(row[8] or 1.0)
            items.append(
                {
                    "model": row[0],
                    "provider": row[1],
                    "requests": int(row[2] or 0),
                    "prompt_tokens": int(row[3] or 0),
                    "completion_tokens": int(row[4] or 0),
                    "total_tokens": int(row[5] or 0),
                    "estimated_cost": float(row[6] or 0.0),
                    "average_latency_ms": float(row[7] or 0.0),
                    "success_rate": success_rate,
                    "failure_rate": max(0.0, 1.0 - success_rate),
                }
            )
        return items

    def _provider_breakdown(
        self,
        *,
        user_id: UUID | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        q = (
            select(
                UsageRecord.provider,
                func.coalesce(func.sum(UsageRecord.request_count), 0),
                func.coalesce(func.sum(UsageRecord.token_usage), 0),
                func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
            )
            .where(UsageRecord.provider.is_not(None))
            .group_by(UsageRecord.provider)
            .order_by(func.sum(UsageRecord.request_count).desc())
        )
        if user_id is not None:
            q = q.where(UsageRecord.user_id == user_id)
        if limit is not None:
            q = q.limit(limit)
        return [
            {
                "provider": row[0],
                "requests": int(row[1] or 0),
                "tokens": int(row[2] or 0),
                "cost": float(row[3] or 0.0),
            }
            for row in self._db.execute(q).all()
        ]

    def _daily_series(
        self,
        *,
        days: int,
        metric: str,
    ) -> list[dict[str, Any]]:
        now = self._now()
        start = self._start_of_day(now) - timedelta(days=days - 1)
        day_expr = func.date_trunc("day", UsageRecord.created_at)
        if metric == "tokens":
            value_expr = func.coalesce(func.sum(UsageRecord.token_usage), 0)
        elif metric == "cost":
            value_expr = func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0)
        else:
            value_expr = func.coalesce(func.sum(UsageRecord.request_count), 0)

        rows = {
            (r[0].date() if hasattr(r[0], "date") else r[0]): float(r[1] or 0)
            for r in self._db.execute(
                select(day_expr, value_expr)
                .where(UsageRecord.created_at >= start)
                .group_by(day_expr)
                .order_by(day_expr)
            ).all()
        }
        points: list[dict[str, Any]] = []
        for offset in range(days):
            d: date = (start + timedelta(days=offset)).date()
            points.append({"label": d.isoformat(), "value": float(rows.get(d, 0.0))})
        return points

    def _most_used_for_user(self, user_id: UUID, column: Any) -> str | None:
        row = self._db.execute(
            select(column, func.coalesce(func.sum(UsageRecord.request_count), 0))
            .where(UsageRecord.user_id == user_id, column.is_not(None))
            .group_by(column)
            .order_by(func.sum(UsageRecord.request_count).desc())
            .limit(1)
        ).first()
        return str(row[0]) if row and row[0] else None

    # ------------------------------------------------------------------ public

    def platform_analytics(self) -> dict[str, object]:
        """Legacy summary used by existing Admin `/admin/usage`."""
        try:
            now = self._now()
            day_ago = now - timedelta(days=1)
            month_ago = now - timedelta(days=30)
            totals = self._window_totals()
            daily = self._window_totals(since=day_ago)
            monthly = self._window_totals(since=month_ago)
            return {
                "total_requests": totals["requests"],
                "daily_requests": daily["requests"],
                "monthly_requests": monthly["requests"],
                "token_usage": totals["tokens"],
                "top_features": self._feature_breakdown(limit=10),
            }
        except Exception as exc:
            logger.error("Failed to load usage analytics: %s", exc)
            raise RepositoryError("Failed to load usage analytics.") from exc

    def analytics_dashboard(self) -> dict[str, Any]:
        try:
            now = self._now()
            today = self._start_of_day(now)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            totals = self._window_totals()
            todays = self._window_totals(since=today)
            weekly = self._window_totals(since=week_ago)
            monthly = self._window_totals(since=month_ago)
            top_users = self._top_users(limit=1)

            return {
                "total_requests": totals["requests"],
                "total_ai_sessions": totals["sessions"],
                "total_prompt_tokens": totals["prompt_tokens"],
                "total_completion_tokens": totals["completion_tokens"],
                "total_tokens_used": totals["tokens"],
                "total_estimated_cost": totals["cost"],
                "average_tokens_per_request": totals["average_tokens_per_request"],
                "average_cost_per_request": totals["average_cost_per_request"],
                "todays_usage": todays,
                "weekly_usage": weekly,
                "monthly_usage": monthly,
                "platform_total_tokens": totals["tokens"],
                "platform_total_cost": totals["cost"],
                "platform_total_requests": totals["requests"],
                "active_users_today": todays["active_users"],
                "most_active_user": top_users[0] if top_users else None,
                "most_used_ai_feature": self._top_feature(),
                "most_used_ai_model": self._top_model(),
                "most_used_provider": self._top_provider(),
                "average_response_time_ms": totals["average_execution_time_ms"],
                "average_execution_time_ms": totals["average_execution_time_ms"],
            }
        except Exception as exc:
            logger.error("Failed to load analytics dashboard: %s", exc)
            raise RepositoryError("Failed to load analytics dashboard.") from exc

    def token_analytics(self) -> dict[str, Any]:
        try:
            now = self._now()
            totals = self._window_totals()
            return {
                "total_prompt_tokens": totals["prompt_tokens"],
                "total_completion_tokens": totals["completion_tokens"],
                "total_tokens": totals["tokens"],
                "daily_tokens": self._window_totals(since=self._start_of_day(now))["tokens"],
                "weekly_tokens": self._window_totals(since=now - timedelta(days=7))["tokens"],
                "monthly_tokens": self._window_totals(since=now - timedelta(days=30))["tokens"],
                "top_users": self._top_users(limit=10),
                "top_features": self._feature_breakdown(limit=10),
                "top_models": self._model_breakdown(limit=10),
                "top_providers": self._provider_breakdown(limit=10),
                "section_token_totals": self._section_token_totals(),
            }
        except Exception as exc:
            logger.error("Failed to load token analytics: %s", exc)
            raise RepositoryError("Failed to load token analytics.") from exc

    def _section_token_totals(self, *, limit: int = 5000) -> dict[str, int]:
        """Aggregate per-section completion tokens across recent usage rows."""
        rows = list(
            self._db.scalars(
                select(UsageRecord)
                .where(UsageRecord.section_tokens.is_not(None))
                .order_by(UsageRecord.created_at.desc())
                .limit(limit)
            ).all()
        )
        totals: dict[str, int] = {}
        for row in rows:
            payload = row.section_tokens
            if not isinstance(payload, dict):
                continue
            for key, value in payload.items():
                try:
                    totals[str(key)] = totals.get(str(key), 0) + int(value)
                except (TypeError, ValueError):
                    continue
        return totals

    def model_analytics(self) -> dict[str, Any]:
        try:
            return {"items": self._model_breakdown()}
        except Exception as exc:
            logger.error("Failed to load model analytics: %s", exc)
            raise RepositoryError("Failed to load model analytics.") from exc

    def provider_analytics(self) -> dict[str, Any]:
        try:
            return {"items": self._provider_breakdown()}
        except Exception as exc:
            logger.error("Failed to load provider analytics: %s", exc)
            raise RepositoryError("Failed to load provider analytics.") from exc

    def feature_analytics(self) -> dict[str, Any]:
        try:
            by_name = {item["feature"]: item for item in self._feature_breakdown()}
            items: list[dict[str, Any]] = []
            for name in KNOWN_FEATURES:
                if name in by_name:
                    items.append(by_name.pop(name))
                else:
                    items.append(
                        {
                            "feature": name,
                            "requests": 0,
                            "tokens": 0,
                            "cost": 0.0,
                            "average_time_ms": 0.0,
                            "average_tokens": 0.0,
                            "average_cost": 0.0,
                        }
                    )
            # Include any unexpected features after known ones
            items.extend(by_name.values())
            return {"items": items}
        except Exception as exc:
            logger.error("Failed to load feature analytics: %s", exc)
            raise RepositoryError("Failed to load feature analytics.") from exc

    def users_analytics(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "total_tokens",
        order: str = "desc",
        user_ids: list[UUID] | None = None,
    ) -> dict[str, Any]:
        try:
            sort_key = SORTABLE_USER_COLUMNS.get(sort, "total_tokens")
            descending = order.lower() != "asc"

            total_requests = func.coalesce(func.sum(UsageRecord.request_count), 0).label(
                "total_requests"
            )
            prompt_tokens = func.coalesce(func.sum(UsageRecord.prompt_tokens), 0).label(
                "prompt_tokens"
            )
            completion_tokens = func.coalesce(
                func.sum(UsageRecord.completion_tokens), 0
            ).label("completion_tokens")
            total_tokens = func.coalesce(func.sum(UsageRecord.token_usage), 0).label(
                "total_tokens"
            )
            estimated_cost = func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0).label(
                "estimated_cost"
            )
            last_active = func.max(UsageRecord.created_at).label("last_active")

            base = select(
                UsageRecord.user_id,
                total_requests,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                estimated_cost,
                last_active,
            ).group_by(UsageRecord.user_id)

            if user_ids is not None:
                if not user_ids:
                    return {"items": [], "total": 0, "page": page, "page_size": page_size}
                base = base.where(UsageRecord.user_id.in_(user_ids))

            count_q = select(func.count()).select_from(base.subquery())
            total = int(self._db.scalar(count_q) or 0)

            sort_col = {
                "total_requests": total_requests,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost": estimated_cost,
                "last_active": last_active,
            }[sort_key]
            ordered = base.order_by(sort_col.desc() if descending else sort_col.asc())
            offset = (page - 1) * page_size
            rows = self._db.execute(ordered.offset(offset).limit(page_size)).all()

            items: list[dict[str, Any]] = []
            for row in rows:
                uid: UUID = row[0]
                requests = int(row[1] or 0)
                tokens = int(row[4] or 0)
                items.append(
                    {
                        "user_id": uid,
                        "total_requests": requests,
                        "prompt_tokens": int(row[2] or 0),
                        "completion_tokens": int(row[3] or 0),
                        "total_tokens": tokens,
                        "estimated_cost": float(row[5] or 0.0),
                        "average_tokens_per_request": (tokens / requests) if requests else 0.0,
                        "last_active": row[6].isoformat() if row[6] else None,
                        "most_used_feature": self._most_used_for_user(uid, UsageRecord.feature),
                        "most_used_model": self._most_used_for_user(uid, UsageRecord.model),
                    }
                )
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        except Exception as exc:
            logger.error("Failed to load users analytics: %s", exc)
            raise RepositoryError("Failed to load users analytics.") from exc

    def batch_user_stats(self, user_ids: list[UUID]) -> dict[str, Any]:
        if not user_ids:
            return {"items": []}
        try:
            data = self.users_analytics(
                page=1,
                page_size=max(len(user_ids), 1),
                sort="total_tokens",
                order="desc",
                user_ids=user_ids,
            )
            return {"items": data["items"]}
        except RepositoryError:
            raise
        except Exception as exc:
            logger.error("Failed to load batch user stats: %s", exc)
            raise RepositoryError("Failed to load batch user stats.") from exc

    def user_detail(self, user_id: UUID) -> dict[str, Any]:
        try:
            totals_q = select(
                func.coalesce(func.sum(UsageRecord.request_count), 0),
                func.coalesce(func.sum(UsageRecord.prompt_tokens), 0),
                func.coalesce(func.sum(UsageRecord.completion_tokens), 0),
                func.coalesce(func.sum(UsageRecord.token_usage), 0),
                func.coalesce(func.sum(UsageRecord.estimated_cost), 0.0),
                func.coalesce(func.avg(UsageRecord.execution_time_ms), 0.0),
                func.max(UsageRecord.created_at),
            ).where(UsageRecord.user_id == user_id)
            row = self._db.execute(totals_q).one()
            requests = int(row[0] or 0)
            tokens = int(row[3] or 0)

            sessions = self._db.execute(
                select(
                    UsageRecord.session_id,
                    func.max(UsageRecord.feature),
                    func.coalesce(func.sum(UsageRecord.token_usage), 0),
                    func.coalesce(func.sum(UsageRecord.execution_time_ms), 0),
                    func.max(UsageRecord.created_at),
                )
                .where(
                    UsageRecord.user_id == user_id,
                    UsageRecord.session_id.is_not(None),
                )
                .group_by(UsageRecord.session_id)
                .order_by(func.max(UsageRecord.created_at).desc())
                .limit(50)
            ).all()

            recent = self.user_usage(user_id, limit=50)

            return {
                "user_id": user_id,
                "total_requests": requests,
                "prompt_tokens": int(row[1] or 0),
                "completion_tokens": int(row[2] or 0),
                "total_tokens": tokens,
                "estimated_cost": float(row[4] or 0.0),
                "average_tokens_per_request": (tokens / requests) if requests else 0.0,
                "average_execution_time_ms": float(row[5] or 0.0),
                "last_activity": row[6].isoformat() if row[6] else None,
                "most_used_feature": self._most_used_for_user(user_id, UsageRecord.feature),
                "most_used_model": self._most_used_for_user(user_id, UsageRecord.model),
                "feature_breakdown": self._feature_breakdown(user_id=user_id),
                "model_usage": self._model_breakdown(user_id=user_id),
                "provider_usage": self._provider_breakdown(user_id=user_id),
                "session_history": [
                    {
                        "session_id": str(s[0]),
                        "feature": s[1],
                        "tokens": int(s[2] or 0),
                        "execution_time_ms": int(s[3] or 0),
                        "last_activity": s[4].isoformat() if s[4] else None,
                    }
                    for s in sessions
                ],
                "recent_conversations": recent,
            }
        except Exception as exc:
            logger.error("Failed to load user detail for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to load user usage detail.") from exc

    def charts(self) -> dict[str, Any]:
        try:
            return {
                "daily_token_usage": self._daily_series(days=30, metric="tokens"),
                "weekly_token_usage": self._daily_series(days=7, metric="tokens"),
                "monthly_token_usage": self._daily_series(days=30, metric="tokens"),
                "requests_per_day": self._daily_series(days=30, metric="requests"),
                "top_features": [
                    {"label": i["feature"], "value": float(i["requests"])}
                    for i in self._feature_breakdown(limit=10)
                ],
                "top_models": [
                    {"label": i["model"], "value": float(i["requests"])}
                    for i in self._model_breakdown(limit=10)
                ],
                "top_providers": [
                    {"label": i["provider"], "value": float(i["requests"])}
                    for i in self._provider_breakdown(limit=10)
                ],
                "top_users": [
                    {"label": str(i["user_id"]), "value": float(i["total_tokens"])}
                    for i in self._top_users(limit=10)
                ],
                "cost_per_day": self._daily_series(days=30, metric="cost"),
                "tokens_per_feature": [
                    {"label": i["feature"], "value": float(i["tokens"])}
                    for i in self._feature_breakdown(limit=10)
                ],
            }
        except Exception as exc:
            logger.error("Failed to load charts: %s", exc)
            raise RepositoryError("Failed to load charts.") from exc

    def cost_analytics(self) -> dict[str, Any]:
        try:
            now = self._now()
            totals = self._window_totals()
            return {
                "total_estimated_cost": totals["cost"],
                "average_cost_per_request": totals["average_cost_per_request"],
                "daily_cost": self._window_totals(since=self._start_of_day(now))["cost"],
                "weekly_cost": self._window_totals(since=now - timedelta(days=7))["cost"],
                "monthly_cost": self._window_totals(since=now - timedelta(days=30))["cost"],
                "cost_by_feature": self._feature_breakdown(),
                "cost_by_model": self._model_breakdown(),
                "cost_by_provider": self._provider_breakdown(),
                "cost_per_day": self._daily_series(days=30, metric="cost"),
            }
        except Exception as exc:
            logger.error("Failed to load cost analytics: %s", exc)
            raise RepositoryError("Failed to load cost analytics.") from exc

    def export_payload(self, report: str) -> dict[str, Any]:
        try:
            report_key = report.strip().lower()
            if report_key == "user_usage":
                data = self.users_analytics(page=1, page_size=10_000)
                columns = [
                    "user_id",
                    "total_requests",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "estimated_cost",
                    "average_tokens_per_request",
                    "last_active",
                    "most_used_feature",
                    "most_used_model",
                ]
                rows = [
                    {c: (str(item[c]) if c == "user_id" else item[c]) for c in columns}
                    for item in data["items"]
                ]
            elif report_key == "feature_usage":
                columns = [
                    "feature",
                    "requests",
                    "tokens",
                    "cost",
                    "average_time_ms",
                    "average_tokens",
                    "average_cost",
                ]
                rows = self._feature_breakdown()
            elif report_key == "model_usage":
                columns = [
                    "model",
                    "provider",
                    "requests",
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "estimated_cost",
                    "average_latency_ms",
                    "success_rate",
                    "failure_rate",
                ]
                rows = self._model_breakdown()
            elif report_key == "provider_usage":
                columns = ["provider", "requests", "tokens", "cost"]
                rows = self._provider_breakdown()
            elif report_key == "token_usage":
                tokens = self.token_analytics()
                columns = [
                    "total_prompt_tokens",
                    "total_completion_tokens",
                    "total_tokens",
                    "daily_tokens",
                    "weekly_tokens",
                    "monthly_tokens",
                ]
                rows = [{c: tokens[c] for c in columns}]
            elif report_key == "cost_analysis":
                costs = self.cost_analytics()
                columns = [
                    "total_estimated_cost",
                    "average_cost_per_request",
                    "daily_cost",
                    "weekly_cost",
                    "monthly_cost",
                ]
                rows = [{c: costs[c] for c in columns}]
            else:
                raise RepositoryError(f"Unknown report type: {report}")
            return {"report": report_key, "rows": rows, "columns": columns}
        except RepositoryError:
            raise
        except Exception as exc:
            logger.error("Failed to build export payload: %s", exc)
            raise RepositoryError("Failed to build export payload.") from exc

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
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "execution_time_ms": r.execution_time_ms,
                    "model": r.model,
                    "provider": r.provider,
                    "estimated_cost": r.estimated_cost,
                    "success": r.success,
                    "session_id": str(r.session_id) if r.session_id else None,
                    "section_tokens": r.section_tokens,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        except Exception as exc:
            logger.error("Failed to load usage for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to load user usage.") from exc
