"""Gateway reverse-proxy routes for admin APIs.

Auth-owned paths (login/refresh/logout/me) stay on Auth Service.
All other ``/admin/*`` management paths go to Admin Service.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["admin-proxy"])

_AUTH_ADMIN_PATHS: set[str] = {"login", "refresh", "logout", "me"}


def _is_auth_admin_path(path: str) -> bool:
    head = path.split("/", 1)[0]
    return head in _AUTH_ADMIN_PATHS


@router.api_route(
    "/admin/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def admin_catchall(request: Request, path: str):
    if _is_auth_admin_path(path):
        return await proxy_to_upstream(
            request,
            upstream_client=request.app.state.auth_client,
            upstream_path=f"/admin/{path}",
            service_name="auth",
            stream=should_stream(request),
        )
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.admin_client,
        upstream_path=f"/admin/{path}",
        service_name="admin",
        stream=should_stream(request),
    )
