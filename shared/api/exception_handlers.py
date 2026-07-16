"""Shared FastAPI exception handler utilities.

Each service registers domain-specific handlers in ``app.api.exception_handlers``
but reuses these helpers for consistent JSON error bodies and request metadata.
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.exceptions.auth import (
    AuthenticationException,
    AuthorizationException,
    ForbiddenError,
    InvalidTokenError,
)
from shared.exceptions.base import BusinessException, ValidationException
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)

INTERNAL_ERROR_DETAIL = "An internal error occurred. Please try again later."
RATE_LIMIT_DETAIL = "Too many requests. Please try again later."


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


def validation_error_detail(exc: RequestValidationError) -> str:
    """Return the first Pydantic validation message for API responses."""
    errors = exc.errors()
    return errors[0]["msg"] if errors else "Validation error."


def register_rate_limit_handler(app: FastAPI) -> None:
    """Attach a 429 handler when slowapi is installed."""
    try:
        from slowapi.errors import RateLimitExceeded
    except ImportError:  # pragma: no cover
        return

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        _request: Request,
        exc: RateLimitExceeded,
    ) -> JSONResponse:
        logger.warning("Rate limit exceeded: %s", exc.detail)
        return error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=RATE_LIMIT_DETAIL,
        )


def register_core_exception_handlers(
    app: FastAPI,
    *,
    validation_status_code: int = status.HTTP_400_BAD_REQUEST,
    include_auth_errors: bool = True,
) -> None:
    """Register cross-service handlers for shared domain exception types."""
    if include_auth_errors:

        @app.exception_handler(InvalidTokenError)
        async def invalid_token_handler(
            _request: Request,
            exc: InvalidTokenError,
        ) -> JSONResponse:
            return error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            )

        @app.exception_handler(AuthenticationException)
        async def authentication_handler(
            _request: Request,
            exc: AuthenticationException,
        ) -> JSONResponse:
            return error_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
                code=exc.code,
            )

        @app.exception_handler(ForbiddenError)
        async def forbidden_handler(
            _request: Request,
            exc: ForbiddenError,
        ) -> JSONResponse:
            return error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
            )

        @app.exception_handler(AuthorizationException)
        async def authorization_handler(
            _request: Request,
            exc: AuthorizationException,
        ) -> JSONResponse:
            return error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(exc),
                code=exc.code,
            )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        _request: Request,
        exc: ValidationException,
    ) -> JSONResponse:
        return error_response(
            status_code=validation_status_code,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(RecordNotFoundError)
    async def not_found_handler(
        _request: Request,
        exc: RecordNotFoundError,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    @app.exception_handler(RepositoryError)
    async def repository_handler(
        _request: Request,
        exc: RepositoryError,
    ) -> JSONResponse:
        logger.error("Repository error: %s", exc, exc_info=True)
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=INTERNAL_ERROR_DETAIL,
        )

    @app.exception_handler(BusinessException)
    async def business_handler(
        _request: Request,
        exc: BusinessException,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=validation_error_detail(exc),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=INTERNAL_ERROR_DETAIL,
        )

