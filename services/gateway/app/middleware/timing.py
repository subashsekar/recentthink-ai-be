"""Gateway edge middleware: request timing and access logging.

Never logs Authorization headers, tokens, passwords, or request bodies.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gateway.access")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Measure request duration and emit a structured access log line."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)

        request_id = getattr(request.state, "request_id", "") or ""
        response.headers["X-Response-Time"] = f"{latency_ms}ms"

        logger.info(
            "access method=%s path=%s status=%s latency_ms=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            request_id,
        )
        return response
