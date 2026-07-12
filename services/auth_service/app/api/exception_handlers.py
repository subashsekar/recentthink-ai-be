"""Global exception handlers for the Auth Service API."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from shared.exceptions import DuplicateEmailError
from shared.exceptions.auth import (
    AuthError,
    AuthenticationException,
    AuthorizationException,
    EmailAlreadyVerifiedError,
    EmailNotVerifiedError,
    ExpiredTokenError,
    ForbiddenError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordReuseError,
    RevokedTokenError,
    UsedTokenError,
    UserNotFoundError,
    BlockedUserError,
)
from shared.exceptions.base import BusinessException, DatabaseException, ValidationException
from shared.exceptions.email import EmailDeliveryError
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


def _error_response(
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    content: dict[str, str] = {"detail": detail}
    if code is not None:
        content["code"] = code
    return JSONResponse(status_code=status_code, content=content)


def _request_context(request: Request) -> dict[str, str]:
    """Extract safe request metadata for logging."""
    request_id = getattr(request.state, "request_id", None)
    ctx: dict[str, str] = {"endpoint": request.url.path}
    if request_id:
        ctx["request_id"] = request_id
    return ctx


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
        request: Request,
        exc: InvalidCredentialsError,
    ) -> JSONResponse:
        log_security_event("login_failure", **_request_context(request))
        logger.warning("Authentication failure: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(AuthenticationException)
    async def authentication_exception_handler(
        request: Request,
        exc: AuthenticationException,
    ) -> JSONResponse:
        log_security_event("unauthorized_access", **_request_context(request))
        logger.warning("Authentication failure: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            code=exc.code,
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
        request: Request,
        exc: InactiveUserError,
    ) -> JSONResponse:
        log_security_event("forbidden_access", reason="inactive", **_request_context(request))
        logger.warning("Inactive user access attempt: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    @app.exception_handler(BlockedUserError)
    async def blocked_user_handler(
        request: Request,
        exc: BlockedUserError,
    ) -> JSONResponse:
        log_security_event("forbidden_access", reason="blocked", **_request_context(request))
        logger.warning("Blocked user access attempt: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
            code="ACCOUNT_BLOCKED",
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        request: Request,
        exc: InvalidTokenError,
    ) -> JSONResponse:
        log_security_event("unauthorized_access", reason="invalid_token", **_request_context(request))
        logger.warning("Invalid token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(ExpiredTokenError)
    async def expired_token_handler(
        request: Request,
        exc: ExpiredTokenError,
    ) -> JSONResponse:
        log_security_event("unauthorized_access", reason="expired_token", **_request_context(request))
        logger.warning("Expired token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(RevokedTokenError)
    async def revoked_token_handler(
        request: Request,
        exc: RevokedTokenError,
    ) -> JSONResponse:
        log_security_event("unauthorized_access", reason="revoked_token", **_request_context(request))
        logger.warning("Revoked token: %s", exc)
        return _error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    @app.exception_handler(UsedTokenError)
    async def used_token_handler(
        _request: Request,
        exc: UsedTokenError,
    ) -> JSONResponse:
        logger.warning("Used token: %s", exc)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(EmailNotVerifiedError)
    async def email_not_verified_handler(
        request: Request,
        exc: EmailNotVerifiedError,
    ) -> JSONResponse:
        log_security_event("forbidden_access", reason="email_not_verified", **_request_context(request))
        logger.warning("Email not verified: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
            code=exc.code or "EMAIL_NOT_VERIFIED",
        )

    @app.exception_handler(EmailAlreadyVerifiedError)
    async def email_already_verified_handler(
        _request: Request,
        exc: EmailAlreadyVerifiedError,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    @app.exception_handler(PasswordReuseError)
    async def password_reuse_handler(
        _request: Request,
        exc: PasswordReuseError,
    ) -> JSONResponse:
        logger.warning("Password reuse rejected: %s", exc)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    @app.exception_handler(EmailDeliveryError)
    async def email_delivery_handler(
        _request: Request,
        exc: EmailDeliveryError,
    ) -> JSONResponse:
        logger.error("Email delivery failure: %s", exc)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later.",
        )

    @app.exception_handler(AuthorizationException)
    async def authorization_exception_handler(
        request: Request,
        exc: AuthorizationException,
    ) -> JSONResponse:
        log_security_event("forbidden_access", **_request_context(request))
        logger.warning("Authorization denied: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden_error_handler(
        request: Request,
        exc: ForbiddenError,
    ) -> JSONResponse:
        log_security_event("forbidden_access", **_request_context(request))
        logger.warning("Authorization denied: %s", exc)
        return _error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(
        _request: Request,
        exc: ValidationException,
    ) -> JSONResponse:
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(DatabaseException)
    async def database_exception_handler(
        _request: Request,
        exc: DatabaseException,
    ) -> JSONResponse:
        logger.error("Database error: %s", exc, exc_info=True)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",
        )

    @app.exception_handler(RepositoryError)
    async def repository_error_handler(
        _request: Request,
        exc: RepositoryError,
    ) -> JSONResponse:
        logger.error("Repository error: %s", exc, exc_info=True)
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",
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

    @app.exception_handler(BusinessException)
    async def business_exception_handler(
        _request: Request,
        exc: BusinessException,
    ) -> JSONResponse:
        logger.warning("Business error: %s", exc)
        return _error_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=exc.code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
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
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
        )
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred. Please try again later.",
        )
