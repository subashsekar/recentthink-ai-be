"""Global exception handlers for the Admin Service."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.clients.base import UpstreamServiceError
from shared.exceptions.auth import (
    AuthenticationException,
    AuthorizationException,
    ForbiddenError,
    InvalidTokenError,
)
from shared.exceptions.base import BusinessException
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


def _error_response(*, status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        _request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    @app.exception_handler(AuthenticationException)
    async def auth_handler(
        _request: Request, exc: AuthenticationException
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(
        _request: Request, exc: ForbiddenError
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @app.exception_handler(AuthorizationException)
    async def authorization_handler(
        _request: Request, exc: AuthorizationException
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    @app.exception_handler(RecordNotFoundError)
    async def not_found_handler(
        _request: Request, exc: RecordNotFoundError
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    @app.exception_handler(UpstreamServiceError)
    async def upstream_handler(
        _request: Request, exc: UpstreamServiceError
    ) -> JSONResponse:
        logger.warning("Upstream service error: %s", exc)
        return _error_response(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        )

    @app.exception_handler(BusinessException)
    async def business_handler(
        _request: Request, exc: BusinessException
    ) -> JSONResponse:
        return _error_response(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    @app.exception_handler(RepositoryError)
    async def repository_handler(
        _request: Request, exc: RepositoryError
    ) -> JSONResponse:
        logger.error("Repository error: %s", exc)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error.",
        )
