"""JWT authentication dependencies for the Admin Service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.exceptions.auth import ForbiddenError, InvalidTokenError
from shared.logging.security import log_security_event
from shared.security.jwt import TokenType, verify_token

_bearer_scheme = HTTPBearer(auto_error=True)

ADMIN_ROLES = frozenset({"ADMIN", "SUPER_ADMIN"})


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: UUID
    email: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role in ADMIN_ROLES


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
) -> AuthenticatedUser:
    payload = verify_token(credentials.credentials)
    if payload.get("token_type") != TokenType.ACCESS.value:
        raise InvalidTokenError("Invalid token type.")
    user_id_raw = payload.get("user_id")
    email = payload.get("email")
    role = payload.get("role")
    if not user_id_raw or not email or not role:
        raise InvalidTokenError("Token payload is incomplete.")
    return AuthenticatedUser(
        user_id=UUID(str(user_id_raw)),
        email=str(email),
        role=str(role),
    )


def require_authenticated_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    return current_user


def require_admin_user(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    if current_user.role not in ADMIN_ROLES:
        log_security_event(
            "forbidden_access",
            user_id=str(current_user.user_id),
            role=current_user.role,
        )
        raise ForbiddenError("Admin privileges required.")
    return current_user
