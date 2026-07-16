"""Gateway reverse-proxy routes for the AI Service.

Catch-all prefixes keep the gateway free of AI business-route duplication.
New AI endpoints under these prefixes work without gateway code changes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.proxy.proxy import proxy_to_upstream
from app.proxy.streaming import should_stream

router = APIRouter(tags=["ai-proxy"])

_AI_PREFIXES: tuple[str, ...] = (
    "leetcode",
    "hackerrank",
    "courses",
    "dsa-pattern",
    "ai",
    "chat",
    "interview",
)


def _proxy_ai(request: Request, prefix: str, path: str):
    upstream_path = f"/{prefix}/{path}" if path else f"/{prefix}"
    return proxy_to_upstream(
        request,
        upstream_client=request.app.state.ai_client,
        upstream_path=upstream_path,
        service_name="ai",
        stream=should_stream(request),
    )


@router.api_route(
    "/leetcode",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/leetcode/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def leetcode_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "leetcode", path)


@router.api_route(
    "/hackerrank",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/hackerrank/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def hackerrank_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "hackerrank", path)


@router.api_route(
    "/courses",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/courses/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def courses_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "courses", path)


@router.api_route(
    "/dsa-pattern",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/dsa-pattern/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def dsa_pattern_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "dsa-pattern", path)


@router.api_route(
    "/ai",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/ai/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def ai_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "ai", path)


@router.api_route(
    "/chat",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/chat/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def chat_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "chat", path)


@router.api_route(
    "/interview",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@router.api_route(
    "/interview/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def interview_proxy(request: Request, path: str = ""):
    return await _proxy_ai(request, "interview", path)


# Keep tuple exported for startup / docs introspection.
__all__ = ["router", "_AI_PREFIXES"]
