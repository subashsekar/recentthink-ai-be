"""Gateway reverse-proxy routes for Auth account management."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["account-proxy"])


@router.api_route(
    "/account",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def account_root(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.auth_client,
        upstream_path="/account",
        service_name="auth",
        stream=should_stream(request),
    )


@router.api_route(
    "/account/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def account_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.auth_client,
        upstream_path=f"/account/{path}",
        service_name="auth",
        stream=should_stream(request),
    )
