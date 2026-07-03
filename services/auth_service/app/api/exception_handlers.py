"""Global exception handlers for the Auth Service API."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from shared.exceptions import DuplicateEmailError
from shared.exceptions.auth import (
    AuthError,
    AuthorizationError,
    ExpiredTokenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RevokedTokenError,
    UserNotFoundError,
)
from shared.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    *,
    status_code: int,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach consistent HTTP handlers for domain and validation errors."""

    @app.exception_handler(DuplicateEmailError)
    async def duplicate_email_handler(
        _request: Request,
        exc: DuplicateEmailError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(
        _request: Request,
        exc: InvalidCredentialsError,
    ) -> JSONResponse:
        logger.warning("Authentication failure: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(
        _request: Request,
        exc: UserNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    @app.exception_handler(InactiveUserError)
    async def inactive_user_handler(
        _request: Request,
        exc: InactiveUserError,
    ) -> JSONResponse:
        logger.warning("Inactive user access attempt: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        _request: Request,
        exc: InvalidTokenError,
    ) -> JSONResponse:
        logger.warning("Invalid token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(ExpiredTokenError)
    async def expired_token_handler(
        _request: Request,
        exc: ExpiredTokenError,
    ) -> JSONResponse:
        logger.warning("Expired token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(RevokedTokenError)
    async def revoked_token_handler(
        _request: Request,
        exc: RevokedTokenError,
    ) -> JSONResponse:
        logger.warning("Revoked token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error_handler(
        _request: Request,
        exc: AuthorizationError,
    ) -> JSONResponse:
        logger.warning("Authorization denied: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        _request: Request,
        exc: RateLimitExceeded,
    ) -> JSONResponse:
        logger.warning("Rate limit exceeded: %s", exc.detail)
        return _error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )

    @app.exception_handler(AuthError)
    async def auth_error_handler(
        _request: Request,
        exc: AuthError,
    ) -> JSONResponse:
        logger.warning("Auth error: %s", exc)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        detail = errors[0]["msg"] if errors else "Validation error."
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )
