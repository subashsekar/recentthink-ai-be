"""Global exception handlers for the AI Service API."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from shared.api.exception_handlers import (
    error_response,
    register_core_exception_handlers,
    register_rate_limit_handler,
)
from shared.exceptions.auth import AuthError
from shared.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""
    register_rate_limit_handler(app)
    register_core_exception_handlers(app)

    @app.exception_handler(AuthError)
    async def auth_error_handler(
        _request: Request,
        exc: AuthError,
    ) -> JSONResponse:
        logger.warning("Auth error: %s", exc)
        return error_response(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
