"""Shared helpers for gateway auth / session-guard tests."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import httpx

from shared.security.jwt import create_access_token


def make_access_token(
    *,
    user_id: UUID | None = None,
    email: str = "user@example.com",
    role: str = "USER",
    pwd_ts: float = 0.0,
    is_verified: bool = True,
) -> tuple[str, UUID]:
    """Return ``(bearer_token, user_id)`` signed with shared settings."""
    uid = user_id or uuid4()
    token = create_access_token(
        user_id=uid,
        email=email,
        role=role,
        pwd_ts=pwd_ts,
        is_verified=is_verified,
    )
    return token, uid


def user_state_response(
    user_id: UUID | str,
    *,
    is_active: bool = True,
    is_blocked: bool = False,
    role: str = "USER",
    pwd_ts: float = 0.0,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "user_id": str(user_id),
            "is_active": is_active,
            "is_blocked": is_blocked,
            "role": role,
            "pwd_ts": pwd_ts,
        },
    )


def with_user_state(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    is_active: bool = True,
    is_blocked: bool = False,
    role: str = "USER",
    pwd_ts: float = 0.0,
) -> Callable[[httpx.Request], httpx.Response]:
    """Wrap a mock upstream handler to answer Auth user-state lookups."""

    def wrapped(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.startswith("/internal/auth/user-state/"):
            uid = path.rsplit("/", 1)[-1]
            return user_state_response(
                uid,
                is_active=is_active,
                is_blocked=is_blocked,
                role=role,
                pwd_ts=pwd_ts,
            )
        return handler(request)

    return wrapped
