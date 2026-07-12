"""Gateway reverse-proxy routes for user notifications."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["notifications-proxy"])


@router.api_route(
    "/notifications",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def notifications_root(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.admin_client,
        upstream_path="/notifications",
        service_name="admin",
        stream=should_stream(request),
    )


@router.api_route(
    "/notifications/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def notifications_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.admin_client,
        upstream_path=f"/notifications/{path}",
        service_name="admin",
        stream=should_stream(request),
    )
