"""Gateway reverse-proxy routes for admin APIs.

Currently forwards to Auth Service (where /admin/* routes exist).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["admin-proxy"])


@router.api_route(
    "/admin/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def admin_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.auth_client,
        upstream_path=f"/admin/{path}",
        stream=should_stream(request),
    )

