"""Shared upstream HTTP client for the gateway.

One pooled ``httpx.AsyncClient`` is created per downstream service at startup
and reused for every request (dependency injection via ``app.state``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from app.core.config import (
    PROXY_CONNECT_TIMEOUT,
    PROXY_POOL_TIMEOUT,
    PROXY_READ_TIMEOUT,
    PROXY_WRITE_TIMEOUT,
)


def build_upstream_client(base_url: str) -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        connect=PROXY_CONNECT_TIMEOUT,
        read=PROXY_READ_TIMEOUT,
        write=PROXY_WRITE_TIMEOUT,
        pool=PROXY_POOL_TIMEOUT,
    )
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=50)
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
    )


@asynccontextmanager
async def upstream_client_lifespan(base_url: str) -> AsyncIterator[httpx.AsyncClient]:
    client = build_upstream_client(base_url)
    try:
        yield client
    finally:
        await client.aclose()
