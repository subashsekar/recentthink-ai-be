"""Gateway session-guard security tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from uuid import uuid4

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
async def test_blocked_user_rejected_before_downstream(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, user_id = make_access_token()
    downstream_hits = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal downstream_hits
        if request.url.path.startswith("/internal/auth/user-state/"):
            return httpx.Response(
                200,
                json={
                    "user_id": str(user_id),
                    "is_active": True,
                    "is_blocked": True,
                    "role": "USER",
                    "pwd_ts": 0.0,
                },
            )
        downstream_hits += 1
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_BLOCKED"
    assert downstream_hits == 0


@pytest.mark.asyncio
async def test_deactivated_user_rejected_before_downstream(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, user_id = make_access_token()
    downstream_hits = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal downstream_hits
        if request.url.path.startswith("/internal/auth/user-state/"):
            return httpx.Response(
                200,
                json={
                    "user_id": str(user_id),
                    "is_active": False,
                    "is_blocked": False,
                    "role": "USER",
                    "pwd_ts": 0.0,
                },
            )
        downstream_hits += 1
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/ai/models",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()
    assert downstream_hits == 0


@pytest.mark.asyncio
async def test_active_user_forwarded(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token()

    def upstream(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/profile"
        assert request.headers.get("authorization") == f"Bearer {token}"
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(
        httpx.MockTransport(with_user_state(upstream))
    ) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_invalid_jwt_rejected(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": "Bearer not-a-jwt"},
        )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token."


@pytest.mark.asyncio
async def test_role_mismatch_rejected(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, user_id = make_access_token(role="USER")

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/internal/auth/user-state/"):
            return httpx.Response(
                200,
                json={
                    "user_id": str(user_id),
                    "is_active": True,
                    "is_blocked": False,
                    "role": "ADMIN",
                    "pwd_ts": 0.0,
                },
            )
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/admin/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_stale_pwd_ts_rejected(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, user_id = make_access_token(pwd_ts=100.0)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/internal/auth/user-state/"):
            return httpx.Response(
                200,
                json={
                    "user_id": str(user_id),
                    "is_active": True,
                    "is_blocked": False,
                    "role": "USER",
                    "pwd_ts": 200.0,
                },
            )
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401
    assert "password change" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_still_public(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/login"
        return httpx.Response(200, json={"access_token": "t"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.post(
            "/auth/login",
            json={"email": "a@b.com", "password": "x"},
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_missing_authorization_still_forwarded(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        return httpx.Response(401, json={"detail": "Unauthorized"})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get("/ai/models")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unknown_user_rejected(
    make_gateway_client: Callable[[httpx.BaseTransport], httpx.AsyncClient],
) -> None:
    token, _uid = make_access_token(user_id=uuid4())

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/internal/auth/user-state/"):
            return httpx.Response(404, json={"detail": "User not found."})
        return httpx.Response(200, json={"ok": True})

    async with make_gateway_client(httpx.MockTransport(handler)) as client:
        resp = await client.get(
            "/profile",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401
