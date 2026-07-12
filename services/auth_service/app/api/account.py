"""Account management HTTP routes (disable / enable / delete / status)."""

from __future__ import annotations

from app.core.rate_limit import ACCOUNT_RATE_LIMIT, limiter
from app.dependencies.auth import get_account_service, require_user
from app.models.user import User
from app.schemas.account import (
    AccountStatusResponse,
    DeleteAccountRequest,
    DisableAccountRequest,
    DisableAccountResponse,
    EnableAccountRequest,
    EnableAccountResponse,
)
from app.schemas.auth import ErrorResponse
from app.services.account_service import AccountService
from fastapi import APIRouter, Depends, Request, status

router = APIRouter(prefix="/account", tags=["account"])

_ERROR_RESPONSES: dict[int | str, dict[str, type[ErrorResponse]]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse},
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
    status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse},
}


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or None
    if request.client is not None:
        return request.client.host
    return None


@router.get(
    "/status",
    response_model=AccountStatusResponse,
    responses=_ERROR_RESPONSES,
    summary="Get account status",
    description=(
        "Return whether the authenticated account is active, blocked, and when "
        "it was disabled (if applicable)."
    ),
)
def get_account_status(
    current_user: User = Depends(require_user),
    account_service: AccountService = Depends(get_account_service),
) -> AccountStatusResponse:
    """Return ``is_active``, ``is_blocked``, and related timestamps."""
    return account_service.get_status(current_user)


@router.patch(
    "/disable",
    response_model=DisableAccountResponse,
    responses=_ERROR_RESPONSES,
    summary="Disable account",
    description=(
        "Temporarily disable the authenticated account. Requires the current "
        "password. All refresh tokens are revoked. Login and refresh are "
        "blocked while disabled. Distinct from admin block (``is_blocked``)."
    ),
)
@limiter.limit(ACCOUNT_RATE_LIMIT)  # type: ignore[untyped-decorator]
def disable_account(
    request: Request,
    payload: DisableAccountRequest,
    current_user: User = Depends(require_user),
    account_service: AccountService = Depends(get_account_service),
) -> DisableAccountResponse:
    """Disable the caller's account after password confirmation."""
    return account_service.disable_account(
        current_user,
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/enable",
    response_model=EnableAccountResponse,
    responses=_ERROR_RESPONSES,
    summary="Enable account",
    description=(
        "Re-enable a self-disabled account using email and password. Does not "
        "require an access token. Blocked accounts cannot self-enable."
    ),
)
@limiter.limit(ACCOUNT_RATE_LIMIT)  # type: ignore[untyped-decorator]
def enable_account(
    request: Request,
    payload: EnableAccountRequest,
    account_service: AccountService = Depends(get_account_service),
) -> EnableAccountResponse:
    """Re-enable a self-disabled account without an active session."""
    return account_service.enable_account(
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **_ERROR_RESPONSES,
        status.HTTP_204_NO_CONTENT: {"description": "Account permanently deleted."},
    },
    summary="Delete account",
    description=(
        "Permanently delete the authenticated account. Requires the current "
        "password and ``confirm=true``. Cascades auth tokens and user profile; "
        "publishes a placeholder AccountDeleted event for other services."
    ),
)
@limiter.limit(ACCOUNT_RATE_LIMIT)  # type: ignore[untyped-decorator]
def delete_account(
    request: Request,
    payload: DeleteAccountRequest,
    current_user: User = Depends(require_user),
    account_service: AccountService = Depends(get_account_service),
) -> None:
    """Permanently delete the caller's account."""
    account_service.delete_account(
        current_user,
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
