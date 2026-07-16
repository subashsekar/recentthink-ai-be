"""HTTP client for Auth Service internal user-state lookups."""

from __future__ import annotations

from uuid import UUID

import httpx

from app.auth.user_state_cache import CachedUserState
from shared.config import get_settings
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER


class UserStateLookupError(Exception):
    """Raised when Auth cannot provide user state (unavailable / not found)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


async def fetch_user_state(
    auth_client: httpx.AsyncClient,
    user_id: UUID,
) -> CachedUserState:
    """Fetch live user state from Auth Service ``GET /internal/auth/user-state/{id}``."""
    settings = get_settings()
    headers = {INTERNAL_SERVICE_TOKEN_HEADER: settings.internal_service_token}
    try:
        response = await auth_client.get(
            f"/internal/auth/user-state/{user_id}",
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise UserStateLookupError(
            "Auth Service unavailable for session check.",
            status_code=503,
        ) from exc

    if response.status_code == 404:
        raise UserStateLookupError("User not found.", status_code=401)
    if response.status_code == 401 or response.status_code == 403:
        raise UserStateLookupError(
            "Internal session check unauthorized.",
            status_code=503,
        )
    if response.status_code >= 400:
        raise UserStateLookupError(
            "Auth Service rejected session check.",
            status_code=503,
        )

    data = response.json()
    return CachedUserState(
        user_id=UUID(str(data["user_id"])),
        is_active=bool(data["is_active"]),
        is_blocked=bool(data["is_blocked"]),
        role=str(data["role"]),
        pwd_ts=float(data.get("pwd_ts") or 0.0),
    )
