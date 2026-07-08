"""Shared upstream HTTP client for the gateway."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx


def build_upstream_client(base_url: str) -> httpx.AsyncClient:
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)
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

