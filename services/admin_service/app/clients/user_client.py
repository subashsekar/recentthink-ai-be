"""User Service internal HTTP client."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.clients.base import BaseInternalClient
from shared.config import Settings, get_settings


class UserServiceClient(BaseInternalClient):
    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(cfg.user_service_url, settings=cfg)

    async def dashboard_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/dashboard-stats")

    async def get_profile_detail(self, user_id: UUID) -> dict[str, Any]:
        return await self._request("GET", f"/internal/admin/profiles/{user_id}")

    async def batch_profiles(self, user_ids: list[UUID]) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/internal/admin/profiles/batch",
            json={"user_ids": [str(uid) for uid in user_ids]},
        )

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
