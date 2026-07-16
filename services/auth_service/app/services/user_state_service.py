"""User-state lookups for gateway session enforcement."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.repositories.user_repository import UserRepository
from app.schemas.user_state import UserStateResponse
from app.services.user_state_cache import (
    get_cached_user_state,
    invalidate_user_state,
    set_cached_user_state,
)
from shared.exceptions.auth import UserNotFoundError


class UserStateService:
    """Resolve the minimal identity fields the gateway needs to enforce access."""

    def __init__(self, *, user_repository: UserRepository) -> None:
        self._users = user_repository

    def get_user_state(self, user_id: UUID) -> UserStateResponse:
        """Return live user state, preferring the process-local cache."""
        cached = get_cached_user_state(user_id)
        if cached is not None:
            return cached

        user = self._users.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User not found.")

        state = UserStateResponse(
            user_id=user.id,
            is_active=user.is_active,
            is_blocked=user.is_blocked,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            pwd_ts=self._password_timestamp(user.password_changed_at),
        )
        set_cached_user_state(state)
        return state

    @staticmethod
    def invalidate(user_id: UUID) -> None:
        """Invalidate cached state after an identity mutation."""
        invalidate_user_state(user_id)

    @staticmethod
    def _password_timestamp(value: datetime | None) -> float:
        if value is None:
            return 0.0
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.timestamp()
