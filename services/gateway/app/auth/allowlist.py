"""Paths that skip gateway session enforcement.

Public credential endpoints must remain reachable without a live user-state
check. Authenticated routes always enforce when a Bearer token is present.
"""

from __future__ import annotations

_PUBLIC_EXACT: frozenset[str] = frozenset(
    {
        "/",
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/auth/verify-email",
        "/auth/resend-verification",
        "/account/enable",
        "/admin/login",
        "/admin/refresh",
    }
)

_PUBLIC_PREFIX_PATHS: tuple[str, ...] = (
    "/media/",
)


def is_public_path(path: str) -> bool:
    """Return True when the gateway must not run the session guard."""
    if path in _PUBLIC_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _PUBLIC_PREFIX_PATHS)
