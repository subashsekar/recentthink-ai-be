"""Dashboard aggregation service (HTTP only)."""

from __future__ import annotations

import asyncio

from app.clients.auth_client import AuthServiceClient
from app.clients.usage_client import UsageServiceClient
from app.clients.user_client import UserServiceClient
from app.schemas.admin import DashboardResponse
from shared.logging import get_logger

logger = get_logger(__name__)


class DashboardService:
    def __init__(
        self,
        *,
        auth_client: AuthServiceClient,
        user_client: UserServiceClient,
        usage_client: UsageServiceClient | None = None,
    ) -> None:
        self._auth = auth_client
        self._user = user_client
        self._usage = usage_client

    async def get_dashboard(self) -> DashboardResponse:
        tasks: list = [
            self._auth.dashboard_stats(),
            self._user.dashboard_stats(),
        ]
        if self._usage is not None:
            tasks.append(self._usage.analytics_dashboard())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        identity = results[0] if not isinstance(results[0], BaseException) else {}
        profiles = results[1] if not isinstance(results[1], BaseException) else {}
        usage: dict = {}
        if self._usage is not None and len(results) > 2:
            if isinstance(results[2], BaseException):
                logger.warning("Usage dashboard stats unavailable: %s", results[2])
            else:
                usage = results[2] or {}

        if not isinstance(identity, dict):
            identity = {}
        if not isinstance(profiles, dict):
            profiles = {}

        return DashboardResponse(
            total_users=int(identity.get("total_users", 0)),
            active_users=int(identity.get("active_users", 0)),
            new_users_today=int(identity.get("new_users_today", 0)),
            verified_users=int(identity.get("verified_users", 0)),
            blocked_users=int(identity.get("blocked_users", 0)),
            students=int(profiles.get("students", 0)),
            professionals=int(profiles.get("professionals", 0)),
            job_seekers=int(profiles.get("job_seekers", 0)),
            platform_total_tokens=int(usage.get("platform_total_tokens", 0)),
            platform_total_cost=float(usage.get("platform_total_cost", 0)),
            platform_total_requests=int(usage.get("platform_total_requests", 0)),
            active_users_today=int(usage.get("active_users_today", 0)),
            most_active_user=usage.get("most_active_user"),
            most_used_ai_feature=usage.get("most_used_ai_feature"),
            most_used_ai_model=usage.get("most_used_ai_model"),
            most_used_provider=usage.get("most_used_provider"),
            average_response_time=float(usage.get("average_response_time_ms", 0)),
            average_execution_time=float(usage.get("average_execution_time_ms", 0)),
        )
