"""Global exception handlers for the Admin Service."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.clients.base import UpstreamServiceError
from shared.api.exception_handlers import (
    error_response,
    register_core_exception_handlers,
    request_context,
)
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""
    register_core_exception_handlers(app)

    @app.exception_handler(UpstreamServiceError)
    async def upstream_handler(
        request: Request,
        exc: UpstreamServiceError,
    ) -> JSONResponse:
        logger.warning("Upstream service error: %s", exc)
        log_security_event("upstream_failure", **request_context(request))
        return error_response(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
