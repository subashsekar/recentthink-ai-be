"""Gateway reverse-proxy routes for the User Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["user-proxy"])


@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def users_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.user_client,
        upstream_path=f"/users/{path}",
        stream=should_stream(request),
    )

