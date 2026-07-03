"""Authentication HTTP routes."""

from __future__ import annotations

from app.core.rate_limit import LOGIN_RATE_LIMIT, REGISTER_RATE_LIMIT, limiter
from app.dependencies.auth import get_auth_service, get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    ErrorResponse,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.schemas.responses import CurrentUserResponse
from app.schemas.token import RefreshTokenRequest, RefreshTokenResponse
from app.services.auth_service import AuthService
from fastapi import APIRouter, Depends, Request, status

router = APIRouter(prefix="/auth", tags=["auth"])

# Consistent error documentation for Swagger/OpenAPI. Every auth endpoint can
# surface these via the shared exception handlers, so they are advertised
# uniformly using the ``ErrorResponse`` schema.
_ERROR_RESPONSES: dict[int | str, dict[str, type[ErrorResponse]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses=_ERROR_RESPONSES,
)
@limiter.limit(REGISTER_RATE_LIMIT)  # type: ignore[untyped-decorator]
def register(
    request: Request,
    payload: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RegisterResponse:
    """Register a new user account."""
    return auth_service.register(payload)


@router.post("/login", response_model=LoginResponse, responses=_ERROR_RESPONSES)
@limiter.limit(LOGIN_RATE_LIMIT)  # type: ignore[untyped-decorator]
def login(
    request: Request,
    payload: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate with email and password."""
    return auth_service.login(payload)


@router.post(
    "/refresh",
    response_model=RefreshTokenResponse,
    responses=_ERROR_RESPONSES,
)
def refresh_token(
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> RefreshTokenResponse:
    """Issue new credentials using a valid refresh token."""
    return auth_service.refresh(payload)


@router.post("/logout", response_model=LogoutResponse, responses=_ERROR_RESPONSES)
def logout(
    payload: LogoutRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LogoutResponse:
    """Revoke the provided refresh token."""
    auth_service.logout(payload)
    return LogoutResponse()


@router.get("/me", response_model=CurrentUserResponse, responses=_ERROR_RESPONSES)
def get_me(
    current_user: User = Depends(get_current_active_user),
) -> CurrentUserResponse:
    """Return the authenticated user's profile."""
    return CurrentUserResponse.model_validate(current_user)
