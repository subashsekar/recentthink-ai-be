"""Gateway reverse-proxy routes for the Auth Service."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["auth-proxy"])


_PUBLIC_AUTH_PATHS: set[str] = {
    "login",
    "register",
    "refresh",
    "verify-email",
    "resend-verification",
    "forgot-password",
    "reset-password",
}


def _auth_requires_auth(path: str) -> bool:
    # /auth/<public> endpoints don't require Authorization.
    head = path.split("/", 1)[0]
    return head not in _PUBLIC_AUTH_PATHS


@router.api_route(
    "/auth/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def auth_catchall(request: Request, path: str):
    return await proxy_to_upstream(
        request,
        upstream_client=request.app.state.auth_client,
        upstream_path=f"/auth/{path}",
        require_auth=_auth_requires_auth(path),
        stream=should_stream(request),
    )

