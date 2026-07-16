"""Global exception handlers for the Usage Service API."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from shared.api.exception_handlers import INTERNAL_ERROR_DETAIL, error_response
from shared.exceptions.auth import AuthenticationException
from shared.exceptions.base import BusinessException, ValidationException
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        _request: Request,
        exc: ValidationException,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(AuthenticationException)
    async def auth_handler(
        _request: Request,
        exc: AuthenticationException,
    ) -> JSONResponse:
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(RecordNotFoundError)
    async def not_found_handler(
        _request: Request,
        exc: RecordNotFoundError,
    ) -> JSONResponse:
        return error_response(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

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
    async def validation_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        detail = errors[0]["msg"] if errors else "Validation error."
        return error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
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
