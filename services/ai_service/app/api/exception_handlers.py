"""Global exception handlers for the AI Service API."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.exceptions.auth import (
    AuthError,
    AuthenticationException,
    AuthorizationException,
    ForbiddenError,
    InvalidTokenError,
)
from shared.exceptions.base import BusinessException, ValidationException
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


def _error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""

    try:
        from slowapi.errors import RateLimitExceeded
    except ImportError:  # pragma: no cover
        RateLimitExceeded = None  # type: ignore[misc, assignment]

    if RateLimitExceeded is not None:

        @app.exception_handler(RateLimitExceeded)
        async def rate_limit_handler(
            _request: Request,
            exc: RateLimitExceeded,
        ) -> JSONResponse:
            logger.warning("Rate limit exceeded: %s", exc.detail)
            return _error_response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
            )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        _request: Request,
        exc: ValidationException,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        _request: Request,
        exc: InvalidTokenError,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    @app.exception_handler(AuthenticationException)
    async def auth_handler(
        _request: Request,
        exc: AuthenticationException,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(
        _request: Request,
        exc: ForbiddenError,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @app.exception_handler(AuthorizationException)
    async def authorization_handler(
        _request: Request,
        exc: AuthorizationException,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @app.exception_handler(RecordNotFoundError)
    async def not_found_handler(
        _request: Request,
        exc: RecordNotFoundError,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    @app.exception_handler(RepositoryError)
    async def repository_handler(
        _request: Request,
        exc: RepositoryError,
    ) -> JSONResponse:
        logger.error("Repository error: %s", exc)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )

    @app.exception_handler(AuthError)
    async def auth_error_handler(
        _request: Request,
        exc: AuthError,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @app.exception_handler(BusinessException)
    async def business_handler(
        _request: Request,
        exc: BusinessException,
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        detail = errors[0]["msg"] if errors else "Validation error."
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred.",
        )
