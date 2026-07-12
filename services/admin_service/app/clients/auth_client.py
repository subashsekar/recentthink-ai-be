"""Auth Service internal HTTP client."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.clients.base import BaseInternalClient
from shared.config import Settings, get_settings


class AuthServiceClient(BaseInternalClient):
    def __init__(self, settings: Settings | None = None) -> None:
        cfg = settings or get_settings()
        super().__init__(cfg.auth_service_url, settings=cfg)

    async def dashboard_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/dashboard-stats")

    async def list_users(self, *, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", "/internal/admin/users", params=params)

    async def get_user(self, user_id: UUID) -> dict[str, Any]:
        return await self._request("GET", f"/internal/admin/users/{user_id}")

    async def list_user_ids(self) -> list[UUID]:
        data = await self._request("GET", "/internal/admin/users/ids")
        return [UUID(str(uid)) for uid in data.get("user_ids", [])]

    async def block_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/internal/admin/users/{user_id}/block",
            actor_id=actor_id,
            json={"reason": reason},
        )

    async def unblock_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/internal/admin/users/{user_id}/unblock",
            actor_id=actor_id,
            json={"reason": reason},
        )

    async def activate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/internal/admin/users/{user_id}/activate",
            actor_id=actor_id,
            json={"reason": reason},
        )

    async def deactivate_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH",
            f"/internal/admin/users/{user_id}/deactivate",
            actor_id=actor_id,
            json={"reason": reason},
        )

    async def delete_user(
        self,
        user_id: UUID,
        *,
        actor_id: UUID,
        reason: str | None = None,
    ) -> None:
        await self._request(
            "DELETE",
            f"/internal/admin/users/{user_id}",
            actor_id=actor_id,
            params={"reason": reason} if reason else None,
        )

    async def health(self) -> tuple[str, float]:
        import time

        start = time.perf_counter()
        try:
            async with __import__("httpx").AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/")
                latency = (time.perf_counter() - start) * 1000
                status = "healthy" if response.status_code < 500 else "down"
                return status, latency
        except Exception:
            return "down", (time.perf_counter() - start) * 1000


def serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
