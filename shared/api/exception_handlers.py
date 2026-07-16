"""Shared FastAPI exception handler utilities.

Each service registers domain-specific handlers in ``app.api.exception_handlers``
but reuses these helpers for consistent JSON error bodies and request metadata.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

INTERNAL_ERROR_DETAIL = "An internal error occurred. Please try again later."


def error_response(
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    """Build a standard ``{"detail": ..., "code": ...}`` JSON error response."""
    content: dict[str, str] = {"detail": detail}
    if code is not None:
        content["code"] = code
    return JSONResponse(status_code=status_code, content=content)


def request_context(request: Request) -> dict[str, str]:
    """Extract safe request metadata for structured logging."""
    request_id = getattr(request.state, "request_id", None)
    ctx: dict[str, str] = {"endpoint": request.url.path}
    if request_id:
        ctx["request_id"] = request_id
    return ctx
