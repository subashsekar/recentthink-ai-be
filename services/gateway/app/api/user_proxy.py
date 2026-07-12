"""Gateway reverse-proxy routes for the User Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["user-proxy"])


@router.api_route(
    "/profile",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def profile_root(request: Request):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.user_client,
        upstream_path="/profile",
        service_name="user",
        stream=should_stream(request),
    )


@router.api_route(
    "/profile/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def profile_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.user_client,
        upstream_path=f"/profile/{path}",
        service_name="user",
        stream=should_stream(request),
    )


@router.api_route(
    "/users/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def users_catchall(request: Request, path: str):
    """Legacy ``/users/*`` catch-all kept for backward compatibility."""
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.user_client,
        upstream_path=f"/users/{path}",
        service_name="user",
        stream=should_stream(request),
    )
