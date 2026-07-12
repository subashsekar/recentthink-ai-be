"""Shared HTTP client helpers for Admin → other services."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from shared.config import Settings, get_settings
from shared.exceptions.base import BusinessException
from shared.exceptions.repository import RecordNotFoundError
from shared.logging import get_logger
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER

logger = get_logger(__name__)


class UpstreamServiceError(BusinessException):
    """Raised when an upstream microservice call fails."""


class BaseInternalClient:
    """HTTP client that authenticates with the internal service token."""

    def __init__(self, base_url: str, *, settings: Settings | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._settings = settings or get_settings()

    def _headers(self, *, actor_id: UUID | None = None) -> dict[str, str]:
        headers = {
            INTERNAL_SERVICE_TOKEN_HEADER: self._settings.internal_service_token,
        }
        if actor_id is not None:
            headers["X-Admin-Actor-Id"] = str(actor_id)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        actor_id: UUID | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float = 15.0,
    ) -> Any:
        url = f"{self._base_url}{path}"
        # Drop None query params
        clean_params = (
            {k: v for k, v in params.items() if v is not None} if params else None
        )
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers(actor_id=actor_id),
                    params=clean_params,
                    json=json,
                )
        except httpx.HTTPError as exc:
            logger.error("Upstream request failed %s %s: %s", method, url, exc)
            raise UpstreamServiceError(f"Upstream service unavailable: {url}") from exc

        if response.status_code == 404:
            detail = _extract_detail(response) or "Resource not found."
            raise RecordNotFoundError(detail)
        if response.status_code >= 400:
            detail = _extract_detail(response) or response.text
            logger.warning(
                "Upstream error %s %s status=%s detail=%s",
                method,
                url,
                response.status_code,
                detail,
            )
            raise UpstreamServiceError(detail)

        if response.status_code == 204 or not response.content:
            return None
        return response.json()


def _extract_detail(response: httpx.Response) -> str | None:
    try:
        data = response.json()
    except ValueError:
        return None
    if isinstance(data, dict):
        detail = data.get("detail")
        if isinstance(detail, str):
            return detail
    return None
