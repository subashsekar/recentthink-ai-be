"""Gateway reverse-proxy tests (multi-service)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import httpx
import pytest


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
        upstream_ai = httpx.AsyncClient(base_url="http://ai-service", transport=transport)
        upstream_auth = httpx.AsyncClient(base_url="http://auth-service", transport=transport)
        upstream_usage = httpx.AsyncClient(base_url="http://usage-service", transport=transport)
        upstream_user = httpx.AsyncClient(base_url="http://user-service", transport=transport)
        upstream_admin = httpx.AsyncClient(base_url="http://admin-service", transport=transport)

        upstreams.extend([upstream_ai, upstream_auth, upstream_usage, upstream_user, upstream_admin])

        gateway_app.state.ai_client = upstream_ai
        gateway_app.state.auth_client = upstream_auth
        gateway_app.state.usage_client = upstream_usage
        gateway_app.state.user_client = upstream_user
        gateway_app.state.admin_client = upstream_admin

        transport_gateway = httpx.ASGITransport(app=gateway_app, lifespan="off")
        return httpx.AsyncClient(transport=transport_gateway, base_url="http://gateway")

    try:
        yield factory
    finally:
        for u in upstreams:
            await u.aclose()


@pytest.mark.asyncio
async def test_missing_authorization_returns_401_and_skips_upstream(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 401
    assert resp.json()["detail"].lower().startswith("missing authorization")
    assert called is False


@pytest.mark.asyncio
async def test_auth_login_does_not_require_authorization(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/login"
        assert request.method == "POST"
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "x"})

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_forwards_path_query_and_authorization_header(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/leetcode/history/abc-123"
        assert request.url.params.get("limit") == "10"
        assert request.headers.get("authorization") == "Bearer test.jwt"
        assert request.headers.get("x-request-id") == "rid-1"
        return httpx.Response(200, json={"ok": True}, headers={"X-Upstream": "yes"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/leetcode/history/abc-123?limit=10",
            headers={"Authorization": "Bearer test.jwt", "X-Request-ID": "rid-1"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert resp.headers["x-upstream"] == "yes"
    assert resp.headers["x-request-id"] == "rid-1"


@pytest.mark.asyncio
async def test_retries_transient_connect_error_then_succeeds(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"attempts": attempts})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models", headers={"Authorization": "Bearer x"})

    assert resp.status_code == 200
    assert resp.json()["attempts"] == 2


class _Stream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for c in self._chunks:
            yield c

    async def aclose(self) -> None:  # pragma: no cover
        return None


@pytest.mark.asyncio
async def test_streaming_passthrough(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/leetcode/analyze"
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=_Stream([b"data: one\n\n", b"data: two\n\n"]),
        )

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post(
            "/leetcode/analyze?stream=true",
            headers={"Authorization": "Bearer x", "Accept": "text/event-stream"},
            json={"problem_url": "x"},
        )
        body = await resp.aread()

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert body == b"data: one\n\ndata: two\n\n"


@pytest.mark.asyncio
async def test_upstream_503_is_passed_through(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"detail": "busy"}, headers={"X-Upstream": "yes"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models", headers={"Authorization": "Bearer x"})

    assert resp.status_code == 503
    assert resp.json()["detail"] == "busy"
    assert resp.headers["x-upstream"] == "yes"

