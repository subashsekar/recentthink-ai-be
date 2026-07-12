"""Statistics business logic."""

from __future__ import annotations

from uuid import UUID

from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository, UserStatistics
from app.schemas.profile import StatisticsResponse
from sqlalchemy.orm import Session

from shared.exceptions.auth import ForbiddenError

ADMIN_ROLES = frozenset({"ADMIN", "SUPER_ADMIN"})


class StatisticsService:
    """Expose read-only learning statistics for a user."""

    def __init__(self, db: Session) -> None:
        self._stats = StatisticsRepository(db)
        self._profiles = ProfileRepository(db)

    def get_statistics(
        self,
        *,
        actor_id: UUID,
        actor_role: str,
        target_user_id: UUID,
        require_profile: bool = True,
    ) -> StatisticsResponse:
        """Return aggregated statistics for ``target_user_id``."""
        if actor_id != target_user_id and actor_role not in ADMIN_ROLES:
            raise ForbiddenError("You do not have permission to view these statistics.")
        if require_profile:
            self._profiles.require_by_user_id(target_user_id)
        raw: UserStatistics = self._stats.get_for_user(target_user_id)
        return StatisticsResponse(
            problems_solved=raw.problems_solved,
            courses_completed=raw.courses_completed,
            patterns_learned=raw.patterns_learned,
            current_streak=raw.current_streak,
            longest_streak=raw.longest_streak,
            learning_hours=raw.learning_hours,
            last_active=raw.last_active,
        )
