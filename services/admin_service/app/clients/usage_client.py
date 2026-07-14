"""Usage Service internal HTTP client."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.clients.base import BaseInternalClient
from shared.config import Settings, get_settings


class UsageServiceClient(BaseInternalClient):
    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(cfg.usage_service_url, settings=cfg)

    async def analytics(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics")

    async def analytics_dashboard(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/dashboard")

    async def analytics_tokens(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/tokens")

    async def analytics_models(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/models")

    async def analytics_providers(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/providers")

    async def analytics_features(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/features")

    async def analytics_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        sort: str = "total_tokens",
        order: str = "desc",
        user_ids: list[UUID] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "page": page,
            "page_size": page_size,
            "sort": sort,
            "order": order,
        }
        if user_ids:
            params["user_ids"] = [str(uid) for uid in user_ids]
        return await self._request(
            "GET",
            "/internal/admin/analytics/users",
            params=params,
        )

    async def analytics_user_detail(self, user_id: UUID) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/internal/admin/analytics/users/{user_id}",
        )

    async def analytics_charts(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/charts")

    async def analytics_costs(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/analytics/costs")

    async def analytics_export(self, report: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/internal/admin/analytics/export",
            params={"report": report},
        )

    async def batch_user_stats(self, user_ids: list[UUID]) -> dict[str, Any]:
        if not user_ids:
            return {"items": []}
        return await self._request(
            "GET",
            "/internal/admin/users/stats",
            params={"user_ids": [str(uid) for uid in user_ids]},
        )

    async def user_usage(self, user_id: UUID) -> dict[str, Any]:
        return await self._request("GET", f"/internal/admin/users/{user_id}")

    async def health(self) -> tuple[str, float]:
        import time

        start = time.perf_counter()
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/")
                latency = (time.perf_counter() - start) * 1000
                status = "healthy" if response.status_code < 500 else "down"
                return status, latency
        except Exception:
            return "down", (time.perf_counter() - start) * 1000
