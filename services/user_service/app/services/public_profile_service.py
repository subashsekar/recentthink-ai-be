"""Public profile assembly."""

from __future__ import annotations

from app.models.profile import UserProfile
from app.models.enums import PrimarySkill
from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository
from app.schemas.profile import (
    PublicProfileListItem,
    PublicProfileResponse,
    PublicProfileSearchResponse,
    StatisticsResponse,
)
from app.utils.validators import normalize_username
from sqlalchemy.orm import Session

from shared.exceptions import RecordNotFoundError
from shared.exceptions.base import ValidationException


_BIO_PREVIEW_MAX_LEN = 200


class PublicProfileService:
    """Build the public-facing profile view (no private fields)."""

    def __init__(self, db: Session) -> None:
        self._profiles = ProfileRepository(db)
        self._stats = StatisticsRepository(db)

    def search(
        self,
        *,
        q: str | None = None,
        primary_skill: PrimarySkill | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PublicProfileSearchResponse:
        """Return paginated public profiles (username required)."""
        skip = (page - 1) * page_size
        profiles, total = self._profiles.list_profiles(
            skip=skip,
            limit=page_size,
            primary_skill=primary_skill,
            name=q.strip() if q else None,
            public_only=True,
        )
        return PublicProfileSearchResponse(
            items=[self._to_list_item(profile) for profile in profiles],
            page=page,
            page_size=page_size,
            total=total,
        )

    @staticmethod
    def _to_list_item(profile: UserProfile) -> PublicProfileListItem:
        bio = profile.bio
        if isinstance(bio, str) and len(bio) > _BIO_PREVIEW_MAX_LEN:
            bio = bio[: _BIO_PREVIEW_MAX_LEN - 3].rstrip() + "..."

        return PublicProfileListItem(
            username=str(profile.username),
            first_name=profile.first_name,
            last_name=profile.last_name,
            primary_skill=profile.primary_skill,
            profile_picture_url=profile.profile_picture_url,
            bio=bio,
        )

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
