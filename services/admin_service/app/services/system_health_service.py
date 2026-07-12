"""System health probes via HTTP."""

from __future__ import annotations

import asyncio
import time

import httpx

from app.clients.ai_client import AIServiceClient
from app.clients.auth_client import AuthServiceClient
from app.clients.usage_client import UsageServiceClient
from app.clients.user_client import UserServiceClient
from app.schemas.admin import HealthResponse, ServiceHealthItem
from shared.database import engine
from sqlalchemy import text


class SystemHealthService:
    def __init__(
        self,
        *,
        auth_client: AuthServiceClient,
        user_client: UserServiceClient,
        ai_client: AIServiceClient,
        usage_client: UsageServiceClient,
    ) -> None:
        self._auth = auth_client
        self._user = user_client
        self._ai = ai_client
        self._usage = usage_client

    async def get_health(self) -> HealthResponse:
        results = await asyncio.gather(
            self._probe_url("gateway", "http://localhost:8000"),
            self._auth.health(),
            self._user.health(),
            self._ai.health(),
            self._usage.health(),
            self._probe_database(),
            return_exceptions=True,
        )

        names = [
            "gateway",
            "auth_service",
            "user_service",
            "ai_service",
            "usage_service",
            "database",
        ]
        services: list[ServiceHealthItem] = []
        for name, result in zip(names, results, strict=True):
            if isinstance(result, Exception):
                services.append(
                    ServiceHealthItem(name=name, status="down", response_time_ms=0.0)
                )
            elif name == "gateway" or name == "database":
                status, latency = result  # type: ignore[misc]
                services.append(
                    ServiceHealthItem(
                        name=name, status=status, response_time_ms=latency
                    )
                )
            else:
                status, latency = result  # type: ignore[misc]
                services.append(
                    ServiceHealthItem(
                        name=name, status=status, response_time_ms=latency
                    )
                )

        # Rename auth/user/ai/usage from health() tuples already named above
        statuses = [s.status for s in services]
        if any(s == "down" for s in statuses):
            overall = "down"
        elif any(s == "warning" for s in statuses):
            overall = "warning"
        else:
            overall = "healthy"
        return HealthResponse(services=services, overall=overall)

    async def _probe_url(self, name: str, url: str) -> tuple[str, float]:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url.rstrip("/") + "/")
                latency = (time.perf_counter() - start) * 1000
                if response.status_code >= 500:
                    return "down", latency
                if latency > 2000:
                    return "warning", latency
                return "healthy", latency
        except Exception:
            return "down", (time.perf_counter() - start) * 1000

    async def _probe_database(self) -> tuple[str, float]:
        start = time.perf_counter()
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start) * 1000
            return ("warning" if latency > 500 else "healthy"), latency
        except Exception:
            return "down", (time.perf_counter() - start) * 1000
