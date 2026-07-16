"""Gateway reverse-proxy tests (multi-service)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from auth_helpers import make_access_token, with_user_state


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

        upstreams.extend(
            [upstream_ai, upstream_auth, upstream_usage, upstream_user, upstream_admin],
        )

        gateway_app.state.ai_client = upstream_ai
        gateway_app.state.auth_client = upstream_auth
        gateway_app.state.usage_client = upstream_usage
        gateway_app.state.user_client = upstream_user
        gateway_app.state.admin_client = upstream_admin

        transport_gateway = httpx.ASGITransport(app=gateway_app)
        return httpx.AsyncClient(transport=transport_gateway, base_url="http://gateway")

    try:
        yield factory
    finally:
        for u in upstreams:
            await u.aclose()


# --- Auth forwarding (session guard skips when no Bearer) -----------------


@pytest.mark.asyncio
async def test_forwards_without_authorization_header(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    """Gateway must not block missing Authorization — downstream owns auth."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        return httpx.Response(401, json={"detail": "Unauthorized"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.asyncio
async def test_auth_login_forwards_body(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/login"
        assert request.method == "POST"
        assert request.headers.get("content-type", "").startswith("application/json")
        assert b"a@b.com" in request.content
        return httpx.Response(200, json={"access_token": "t"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post("/auth/login", json={"email": "a@b.com", "password": "x"})

    assert resp.status_code == 200
    assert resp.json() == {"access_token": "t"}


@pytest.mark.asyncio
async def test_forwards_authorization_bearer_token(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == f"Bearer {token}"
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_forwards_path_query_and_custom_headers(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/leetcode/history/abc-123"
        assert request.url.params.get("limit") == "10"
        assert request.headers.get("authorization") == f"Bearer {token}"
        assert request.headers.get("x-request-id") == "rid-1"
        assert request.headers.get("accept") == "application/json"
        assert request.headers.get("x-custom-client") == "fe"
        return httpx.Response(200, json={"ok": True}, headers={"X-Upstream": "yes"})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.get(
            "/leetcode/history/abc-123?limit=10",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Request-ID": "rid-1",
                "Accept": "application/json",
                "X-Custom-Client": "fe",
            },
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert resp.headers["x-upstream"] == "yes"
    assert resp.headers["x-request-id"] == "rid-1"


@pytest.mark.asyncio
async def test_forwards_json_body_on_patch(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert request.url.path == "/leetcode/history/abc-123"
        assert request.content == b'{"model_id":"openai/gpt-4o-mini"}'
        return httpx.Response(
            200,
            json={"id": "abc-123", "model_id": "openai/gpt-4o-mini"},
        )

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.patch(
            "/leetcode/history/abc-123",
            headers={"Authorization": f"Bearer {token}"},
            json={"model_id": "openai/gpt-4o-mini"},
        )

    assert resp.status_code == 200
    assert resp.json()["model_id"] == "openai/gpt-4o-mini"


# --- Service routing ------------------------------------------------------


@pytest.mark.asyncio
async def test_hackerrank_catchall_routes_to_ai(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hackerrank/analyze"
        assert str(request.url).startswith("http://ai-service/")
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.post(
            "/hackerrank/analyze",
            headers={"Authorization": f"Bearer {token}"},
            json={"problem_url": "x"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_login_routes_to_auth(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/admin/login"
        assert str(request.url).startswith("http://auth-service/")
        return httpx.Response(200, json={"access_token": "admin"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post(
            "/admin/login",
            json={"email": "admin@x.com", "password": "x"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_dashboard_routes_to_admin_service(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token(role="ADMIN")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/admin/dashboard"
        assert str(request.url).startswith("http://admin-service/")
        return httpx.Response(200, json={"users": 1})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler, role="ADMIN"))
    ) as client:
        resp = await client.get(
            "/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_usage_routes_to_usage_service(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/usage/record"
        assert str(request.url).startswith("http://usage-service/")
        return httpx.Response(201, json={"recorded": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post("/usage/record", json={"tokens": 10})

    assert resp.status_code == 201


# --- Uploads --------------------------------------------------------------


@pytest.mark.asyncio
async def test_multipart_upload_forwarded(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/profile/avatar"
        ctype = request.headers.get("content-type", "")
        assert ctype.startswith("multipart/form-data")
        assert b"fake-image-bytes" in request.content
        return httpx.Response(200, json={"profile_picture_url": "http://x/a.png"})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.post(
            "/profile/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("avatar.png", b"fake-image-bytes", "image/png")},
        )

    assert resp.status_code == 200
    assert "profile_picture_url" in resp.json()


# --- Streaming / retries / errors -----------------------------------------


@pytest.mark.asyncio
async def test_retries_transient_connect_error_then_succeeds(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json={"attempts": attempts})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.get(
            "/ai/models",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["attempts"] == 2


@pytest.mark.asyncio
async def test_connect_error_returns_502(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 502
    assert resp.json()["detail"] == "Bad Gateway"


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
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/leetcode/analyze"
        return httpx.Response(
            200,
            headers={"Content-Type": "text/event-stream"},
            stream=_Stream([b"data: one\n\n", b"data: two\n\n"]),
        )

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.post(
            "/leetcode/analyze?stream=true",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "text/event-stream",
            },
            json={"problem_url": "x"},
        )
        body = await resp.aread()

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert body == b"data: one\n\ndata: two\n\n"


@pytest.mark.asyncio
async def test_cors_preflight_allows_localhost_3001(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3001"
    assert called is False


@pytest.mark.asyncio
async def test_chat_proxy_forwards_to_ai_service(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chat/leetcode/sessions"
        return httpx.Response(
            200,
            json={"sessions": [], "total": 0, "limit": 50, "offset": 0},
        )

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.get(
            "/chat/leetcode/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_upstream_503_is_passed_through_after_retries(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, json={"detail": "busy"}, headers={"X-Upstream": "yes"})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(handler))
    ) as client:
        resp = await client.get(
            "/ai/models",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 503
    assert resp.json()["detail"] == "busy"
    assert resp.headers["x-upstream"] == "yes"
    assert calls == 3  # default retry attempts


@pytest.mark.asyncio
async def test_generates_request_id_when_missing(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        rid = request.headers.get("x-request-id", "")
        seen.append(rid)
        assert rid
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")
    assert seen[0] == resp.headers["x-request-id"]
