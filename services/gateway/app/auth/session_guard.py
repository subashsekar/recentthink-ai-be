"""Gateway session guard: JWT validity + live Auth user state.

Preserves the existing JWT issue/refresh flow. Downstream services still verify
signatures; the gateway additionally rejects blocked / deactivated accounts
before traffic reaches User / AI / Admin.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.auth.allowlist import is_public_path
from app.auth.user_state_cache import (
    CachedUserState,
    get_cached,
    set_cached,
)
from app.auth.user_state_client import UserStateLookupError, fetch_user_state
from app.core.config import (
    SESSION_GUARD_ENABLED,
    USER_STATE_CACHE_TTL_SECONDS,
)
from shared.exceptions.auth import ExpiredTokenError, InvalidTokenError
from shared.middleware.request_id import REQUEST_ID_HEADER
from shared.security.jwt import TokenType, verify_token

logger = logging.getLogger("gateway.session_guard")


@dataclass(frozen=True, slots=True)
class SessionGuardResult:
    """Outcome of a session-guard evaluation."""

    allowed: bool
    response: JSONResponse | None = None


def _request_id(request: Request) -> str:
    rid = getattr(request.state, "request_id", None)
    if isinstance(rid, str) and rid:
        return rid
    header_val = request.headers.get(REQUEST_ID_HEADER)
    return header_val or ""


def _error_response(
    request: Request,
    *,
    status_code: int,
    detail: str,
    code: str | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {"detail": detail}
    if code:
        body["code"] = code
    headers: dict[str, str] = {}
    rid = _request_id(request)
    if rid:
        headers[REQUEST_ID_HEADER] = rid
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        return None
    return parts[1].strip()


def _pwd_ts_stale(token_pwd_ts: object, current: float) -> bool:
    if current <= 0:
        return False
    if not isinstance(token_pwd_ts, (int, float)) or isinstance(token_pwd_ts, bool):
        return True
    return float(token_pwd_ts) < current


def _evaluate_state(
    request: Request,
    *,
    payload: dict[str, Any],
    state: CachedUserState,
) -> SessionGuardResult:
    if state.is_blocked:
        logger.warning(
            "session_guard blocked user_id=%s path=%s",
            state.user_id,
            request.url.path,
        )
        return SessionGuardResult(
            allowed=False,
            response=_error_response(
                request,
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been blocked.",
                code="ACCOUNT_BLOCKED",
            ),
        )
    if not state.is_active:
        logger.warning(
            "session_guard inactive user_id=%s path=%s",
            state.user_id,
            request.url.path,
        )
        return SessionGuardResult(
            allowed=False,
            response=_error_response(
                request,
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been disabled.",
            ),
        )

    token_role = str(payload.get("role") or "")
    if token_role != state.role:
        logger.warning(
            "session_guard role_mismatch user_id=%s token_role=%s live_role=%s",
            state.user_id,
            token_role,
            state.role,
        )
        return SessionGuardResult(
            allowed=False,
            response=_error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            ),
        )

    if _pwd_ts_stale(payload.get("pwd_ts"), state.pwd_ts):
        logger.warning(
            "session_guard stale_pwd_ts user_id=%s path=%s",
            state.user_id,
            request.url.path,
        )
        return SessionGuardResult(
            allowed=False,
            response=_error_response(
                request,
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to a password change. Please log in again.",
            ),
        )

    return SessionGuardResult(allowed=True)


async def enforce_session(request: Request) -> JSONResponse | None:
    """Validate JWT + live user state when a Bearer token is present.

    Returns a JSON error response to short-circuit the proxy, or ``None`` to
    allow forwarding. Missing Authorization is intentionally allowed — public
    and credential endpoints, and downstream-owned 401s, remain unchanged.
    """
    if not SESSION_GUARD_ENABLED:
        return None

    path = request.url.path
    if is_public_path(path):
        return None

    token = _extract_bearer(request)
    if token is None:
        return None

    try:
        payload = verify_token(token)
    except ExpiredTokenError:
        return _error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except InvalidTokenError:
        return _error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    if payload.get("token_type") != TokenType.ACCESS.value:
        return _error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    raw_user_id = payload.get("user_id")
    try:
        user_id = UUID(str(raw_user_id))
    except (TypeError, ValueError):
        return _error_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )

    state = get_cached(user_id)
    if state is None:
        auth_client = getattr(request.app.state, "auth_client", None)
        if not isinstance(auth_client, httpx.AsyncClient):
            return _error_response(
                request,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Session check unavailable.",
            )
        try:
            state = await fetch_user_state(auth_client, user_id)
        except UserStateLookupError as exc:
            code = exc.status_code or status.HTTP_503_SERVICE_UNAVAILABLE
            if code == 401:
                return _error_response(
                    request,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token.",
                )
            return _error_response(
                request,
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            )
        set_cached(state, ttl_seconds=USER_STATE_CACHE_TTL_SECONDS)

    result = _evaluate_state(request, payload=payload, state=state)
    return result.response
