"""Usage service HTTP client."""

from __future__ import annotations

from uuid import UUID

import httpx

from shared.config import Settings, get_settings
from shared.logging import get_logger
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER

logger = get_logger(__name__)


class UsageServiceClient:
    """Records metering events with the Usage Service."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._base_url = self._settings.usage_service_url.rstrip("/")

    async def record_usage(
        self,
        *,
        user_id: UUID,
        feature: str,
        token_usage: int,
        execution_time_ms: int,
        session_id: UUID | None = None,
        request_count: int = 1,
    ) -> None:
        payload = {
            "user_id": str(user_id),
            "service_name": "ai_service",
            "feature": feature,
            "request_count": request_count,
            "token_usage": token_usage,
            "execution_time_ms": execution_time_ms,
            "session_id": str(session_id) if session_id else None,
        }
        url = f"{self._base_url}/usage/record"
        headers = {
            INTERNAL_SERVICE_TOKEN_HEADER: self._settings.internal_service_token,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Failed to record usage for user_id=%s: %s", user_id, exc)
