"""Public profile assembly."""

from __future__ import annotations

from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository
from app.schemas.profile import PublicProfileResponse, StatisticsResponse
from app.utils.validators import normalize_username
from sqlalchemy.orm import Session

from shared.exceptions import RecordNotFoundError
from shared.exceptions.base import ValidationException


class PublicProfileService:
    """Build the public-facing profile view (no private fields)."""

    def __init__(self, db: Session) -> None:
        self._profiles = ProfileRepository(db)
        self._stats = StatisticsRepository(db)

    def get_by_username(self, username: str) -> PublicProfileResponse:
        """Return the public profile for ``username``."""
        normalized = normalize_username(username)
        if normalized is None:
            raise ValidationException("Invalid username.")

        profile = self._profiles.get_by_username(normalized)
        if profile is None or not profile.username:
            raise RecordNotFoundError("Profile not found.")

        raw = self._stats.get_for_user(profile.user_id)
        return PublicProfileResponse(
            username=profile.username,
            first_name=profile.first_name,
            last_name=profile.last_name,
            bio=profile.bio,
            github_username=profile.github_username,
            linkedin_url=profile.linkedin_url,
            portfolio_url=profile.portfolio_url,
            primary_skill=profile.primary_skill,
            profile_picture_url=profile.profile_picture_url,
            statistics=StatisticsResponse(
                problems_solved=raw.problems_solved,
                courses_completed=raw.courses_completed,
                patterns_learned=raw.patterns_learned,
                current_streak=raw.current_streak,
                longest_streak=raw.longest_streak,
                learning_hours=raw.learning_hours,
                last_active=raw.last_active,
            ),
        )
