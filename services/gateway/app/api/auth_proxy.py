"""Gateway reverse-proxy routes for the Auth Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["auth-proxy"])


@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def auth_catchall(request: Request, path: str):
    # OPTIONS preflight is handled by CORSMiddleware — do not proxy it upstream.
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.auth_client,
        upstream_path=f"/auth/{path}",
        service_name="auth",
        stream=should_stream(request),
    )
