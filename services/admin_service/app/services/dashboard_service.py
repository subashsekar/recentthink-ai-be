"""Dashboard aggregation service (HTTP only)."""

from __future__ import annotations

import asyncio

from app.clients.auth_client import AuthServiceClient
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
    ) -> None:
        self._auth = auth_client
        self._user = user_client

    async def get_dashboard(self) -> DashboardResponse:
        identity, profiles = await asyncio.gather(
            self._auth.dashboard_stats(),
            self._user.dashboard_stats(),
        )
        return DashboardResponse(
            total_users=int(identity.get("total_users", 0)),
            active_users=int(identity.get("active_users", 0)),
            new_users_today=int(identity.get("new_users_today", 0)),
            verified_users=int(identity.get("verified_users", 0)),
            blocked_users=int(identity.get("blocked_users", 0)),
            students=int(profiles.get("students", 0)),
            professionals=int(profiles.get("professionals", 0)),
            job_seekers=int(profiles.get("job_seekers", 0)),
        )
