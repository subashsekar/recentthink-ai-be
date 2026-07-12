"""Health check business logic for the API Gateway."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from fastapi import Request

from app.core.config import APP_VERSION, HEALTH_PROBE_TIMEOUT, SERVICE_NAME
from app.schemas.health import (
    DownstreamServiceHealth,
    GatewayHealthResponse,
    ServiceStatus,
)
from shared.config import get_settings
from shared.schemas.health import HealthResponse, build_health_response

_WARNING_THRESHOLD_MS = 1000


def get_health_status() -> HealthResponse:
    """Build the lightweight gateway-only health payload (liveness)."""
    return build_health_response(SERVICE_NAME)


def _classify_latency(elapsed_ms: int, http_ok: bool) -> ServiceStatus:
    if not http_ok:
        return "down"
    if elapsed_ms >= _WARNING_THRESHOLD_MS:
        return "warning"
    return "healthy"


async def _probe_service(
    name: str,
    client: httpx.AsyncClient,
    url: str,
) -> DownstreamServiceHealth:
    start = time.perf_counter()
    try:
        resp = await client.get("/", timeout=HEALTH_PROBE_TIMEOUT)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        http_ok = 200 <= resp.status_code < 500
        status = _classify_latency(elapsed_ms, http_ok)
        detail = None if http_ok else f"HTTP {resp.status_code}"
        await resp.aclose()
        return DownstreamServiceHealth(
            name=name,
            status=status,
            response_time_ms=elapsed_ms,
            url=url,
            detail=detail,
        )
    except Exception as exc:  # noqa: BLE001 — surface any probe failure as down
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return DownstreamServiceHealth(
            name=name,
            status="down",
            response_time_ms=elapsed_ms,
            url=url,
            detail=str(exc.__class__.__name__),
        )


def _aggregate_status(statuses: list[ServiceStatus]) -> ServiceStatus:
    if not statuses:
        return "down"
    if all(s == "healthy" for s in statuses):
        return "healthy"
    if all(s == "down" for s in statuses):
        return "down"
    return "warning"


async def get_aggregate_health(request: Request) -> GatewayHealthResponse:
    """Probe every downstream service and return an aggregated health report."""
    cfg = get_settings()
    state: Any = request.app.state

    probes = [
        ("auth", state.auth_client, cfg.auth_service_url),
        ("user", state.user_client, cfg.user_service_url),
        ("admin", state.admin_client, cfg.admin_service_url),
        ("ai", state.ai_client, cfg.ai_service_url),
        ("usage", state.usage_client, cfg.usage_service_url),
    ]

    results = await asyncio.gather(
        *[_probe_service(name, client, url) for name, client, url in probes],
    )
    overall = _aggregate_status([r.status for r in results])
    return GatewayHealthResponse(
        service=SERVICE_NAME,
        status=overall,
        version=APP_VERSION,
        environment=cfg.environment.value,
        services=list(results),
    )
