"""Gateway reverse-proxy routes for the Usage Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["usage-proxy"])


@router.api_route(
    "/usage/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def usage_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.usage_client,
        upstream_path=f"/usage/{path}",
        service_name="usage",
        stream=should_stream(request),
    )
