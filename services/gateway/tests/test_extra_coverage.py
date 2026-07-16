"""Additional gateway route and error-path coverage."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.proxy.client import build_upstream_client
from app.services.health_service import _aggregate_status, _classify_latency


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

        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=gateway_app),
            base_url="http://gateway",
        )

    try:
        yield factory
    finally:
        for u in upstreams:
            await u.aclose()


@pytest.mark.asyncio
async def test_account_and_notifications_forward(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.url.host}{request.url.path}")
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        r1 = await client.get("/account/status", headers={"Authorization": "Bearer x"})
        r2 = await client.get("/notifications", headers={"Authorization": "Bearer x"})
        r3 = await client.get("/notifications/1", headers={"Authorization": "Bearer x"})
        r4 = await client.get("/account", headers={"Authorization": "Bearer x"})

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert r4.status_code == 200
    assert "auth-service/account/status" in seen
    assert "admin-service/notifications" in seen
    assert "admin-service/notifications/1" in seen
    assert "auth-service/account" in seen


@pytest.mark.asyncio
async def test_courses_dsa_and_users_routes(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        assert (
            await client.get("/courses/history", headers={"Authorization": "Bearer x"})
        ).status_code == 200
        assert (
            await client.get("/dsa-pattern/examples", headers={"Authorization": "Bearer x"})
        ).status_code == 200
        assert (
            await client.get("/users/me", headers={"Authorization": "Bearer x"})
        ).status_code == 200
        assert (
            await client.get("/users/search?q=jane", headers={"Authorization": "Bearer x"})
        ).status_code == 200
        assert (await client.get("/media/avatars/test.jpg")).status_code == 200

    assert "/courses/history" in seen
    assert "/dsa-pattern/examples" in seen
    assert "/users/me" in seen
    assert "/profile/search" in seen
    assert "/media/avatars/test.jpg" in seen


@pytest.mark.asyncio
async def test_read_timeout_returns_504(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 504
    assert resp.json()["detail"] == "Gateway Timeout"


@pytest.mark.asyncio
async def test_build_upstream_client_reuses_timeouts() -> None:
    client = build_upstream_client("http://example.test")
    try:
        assert str(client.base_url) == "http://example.test"
        assert client.timeout.connect == 5.0
    finally:
        await client.aclose()


def test_classify_latency_and_aggregate() -> None:
    assert _classify_latency(10, True) == "healthy"
    assert _classify_latency(1500, True) == "warning"
    assert _classify_latency(10, False) == "down"
    assert _aggregate_status([]) == "down"
    assert _aggregate_status(["healthy", "healthy"]) == "healthy"
    assert _aggregate_status(["down", "down"]) == "down"
    assert _aggregate_status(["healthy", "down"]) == "warning"


def test_proxy_request_id_from_state_when_header_absent() -> None:
    from app.proxy.proxy import _request_id

    request = MagicMock()
    request.state.request_id = "from-state"
    request.headers = {}
    assert _request_id(request) == "from-state"


@pytest.mark.asyncio
async def test_upstream_client_lifespan_closes() -> None:
    from app.proxy.client import upstream_client_lifespan

    async with upstream_client_lifespan("http://localhost:9") as client:
        assert str(client.base_url).startswith("http://localhost:9")


def test_request_id_falls_back_to_header() -> None:
    from app.proxy.proxy import _request_id
    from shared.middleware.request_id import REQUEST_ID_HEADER

    request = MagicMock()
    request.state = MagicMock(spec=[])  # no request_id attr
    # getattr(state, "request_id", None) returns a MagicMock by default — force None path
    del request.state.request_id
    request.state = type("S", (), {})()
    request.headers = {REQUEST_ID_HEADER: "hdr-1"}
    assert _request_id(request) == "hdr-1"

    request2 = MagicMock()
    request2.state = type("S", (), {})()
    request2.headers = {}
    assert _request_id(request2) == ""


def test_should_enable_trusted_host() -> None:
    from app.main import should_enable_trusted_host

    assert should_enable_trusted_host(["*"]) is False
    assert should_enable_trusted_host(["api.recentthink.com"]) is True


def test_configure_trusted_host_adds_middleware() -> None:
    from fastapi import FastAPI

    from app.main import configure_trusted_host

    application = FastAPI()
    with patch.object(application, "add_middleware") as add_mw:
        configure_trusted_host(application, hosts=["api.example.com"])
    add_mw.assert_called_once()

    application2 = FastAPI()
    with patch.object(application2, "add_middleware") as add_mw2:
        configure_trusted_host(application2, hosts=["*"])
    add_mw2.assert_not_called()


def test_log_startup_emits_routes() -> None:
    from app.main import _log_startup, app

    with patch("app.main.logger") as mock_logger:
        _log_startup(app)
    assert mock_logger.info.called


def test_lifespan_via_testclient_sets_upstream_clients() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert app.state.ai_client is not None
        assert app.state.auth_client is not None
        assert app.state.user_client is not None
        assert app.state.admin_client is not None
        assert app.state.usage_client is not None
