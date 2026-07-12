"""Health endpoint tests for the API Gateway."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the API Gateway (liveness only)."""
    from app.main import app

    return TestClient(app)


def test_liveness_endpoint_returns_200(client: TestClient) -> None:
    """GET / should return HTTP 200 with gateway health payload."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "gateway"
    assert data["status"] == "healthy"


@pytest.fixture
async def gateway_app() -> AsyncIterator[object]:
    from app.main import app

    yield app


@pytest.fixture
async def make_gateway_client(
    gateway_app: object,
) -> AsyncIterator[Callable[[httpx.BaseTransport], httpx.AsyncClient]]:
    upstreams: list[httpx.AsyncClient] = []

    def factory(transport: httpx.BaseTransport) -> httpx.AsyncClient:
        for name, base in [
            ("ai", "http://ai-service"),
            ("auth", "http://auth-service"),
            ("usage", "http://usage-service"),
            ("user", "http://user-service"),
            ("admin", "http://admin-service"),
        ]:
            c = httpx.AsyncClient(base_url=base, transport=transport)
            upstreams.append(c)
            setattr(gateway_app.state, f"{name}_client", c)

        transport_gateway = httpx.ASGITransport(app=gateway_app)
        return httpx.AsyncClient(transport=transport_gateway, base_url="http://gateway")

    try:
        yield factory
    finally:
        for u in upstreams:
            await u.aclose()


@pytest.mark.asyncio
async def test_aggregate_health_all_healthy(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/"
        return httpx.Response(200, json={"service": "x", "status": "healthy"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "gateway"
    assert data["status"] == "healthy"
    assert data["version"]
    assert len(data["services"]) == 5
    names = {s["name"] for s in data["services"]}
    assert names == {"auth", "user", "admin", "ai", "usage"}
    assert all(s["status"] == "healthy" for s in data["services"])
    assert all(s["response_time_ms"] is not None for s in data["services"])


@pytest.mark.asyncio
async def test_aggregate_health_partial_failure_is_warning(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        if host == "ai-service":
            raise httpx.ConnectError("down", request=request)
        return httpx.Response(200, json={"service": "x", "status": "healthy"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "warning"
    by_name = {s["name"]: s for s in data["services"]}
    assert by_name["ai"]["status"] == "down"
    assert by_name["auth"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_aggregate_health_all_down(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "down"
    assert all(s["status"] == "down" for s in data["services"])
