"""Profile data-access repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.profile import UserProfile
from app.models.enums import CurrentStatus, PrimarySkill
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import DuplicateUsernameError, RecordNotFoundError, RepositoryError
from shared.exceptions.base import BusinessException
from shared.logging import get_logger

logger = get_logger(__name__)


class ProfileRepository:
    """Repository for :class:`UserProfile` persistence."""

    EDITABLE_FIELDS: frozenset[str] = frozenset(
        {
            "username",
            "first_name",
            "last_name",
            "mobile_number",
            "profile_picture_url",
            "bio",
            "current_status",
            "college",
            "company",
            "current_role",
            "experience_years",
            "primary_skill",
            "leetcode_username",
            "hackerrank_username",
            "github_username",
            "linkedin_url",
            "portfolio_url",
        }
    )

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_profile(self, *, user_id: UUID, **fields: Any) -> UserProfile:
        """Persist a new profile for ``user_id``."""
        if self.get_by_user_id(user_id) is not None:
            raise BusinessException("Profile already exists for this user.")

        username = fields.get("username")
        if username and self.get_by_username(str(username)) is not None:
            raise DuplicateUsernameError(f"Username '{username}' is already taken.")

        payload = {key: value for key, value in fields.items() if key in self.EDITABLE_FIELDS}
        profile = UserProfile(user_id=user_id, **payload)
        try:
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
            logger.info("Created profile user_id=%s id=%s", user_id, profile.id)
            return profile
        except IntegrityError as exc:
            self._db.rollback()
            logger.warning("Integrity error creating profile user_id=%s: %s", user_id, exc)
            raise DuplicateUsernameError("Username is already taken.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating profile user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to create profile.") from exc

    def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        """Return a profile by owning user id."""
        try:
            return self._db.scalar(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching profile user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to fetch profile.") from exc

    def get_by_username(self, username: str) -> UserProfile | None:
        """Return a profile by public username (case-insensitive storage)."""
        try:
            return self._db.scalar(
                select(UserProfile).where(UserProfile.username == username.lower())
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching profile username=%s: %s", username, exc)
            raise RepositoryError("Failed to fetch profile.") from exc

    def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        """Return a profile by primary key."""
        try:
            return self._db.scalar(select(UserProfile).where(UserProfile.id == profile_id))
        except SQLAlchemyError as exc:
            logger.error("Database error fetching profile id=%s: %s", profile_id, exc)
            raise RepositoryError("Failed to fetch profile.") from exc

    def update_profile(self, user_id: UUID, **fields: Any) -> UserProfile:
        """Update editable fields for the profile owned by ``user_id``."""
        profile = self.get_by_user_id(user_id)
        if profile is None:
            raise RecordNotFoundError("Profile not found.")

        unknown = set(fields) - self.EDITABLE_FIELDS
        if unknown:
            raise ValueError(f"Non-editable fields: {sorted(unknown)}")

        if "username" in fields and fields["username"]:
            existing = self.get_by_username(str(fields["username"]))
            if existing is not None and existing.user_id != user_id:
                raise DuplicateUsernameError(
                    f"Username '{fields['username']}' is already taken.",
                )

        for key, value in fields.items():
            setattr(profile, key, value)

        try:
            self._db.add(profile)
            self._db.commit()
            self._db.refresh(profile)
            logger.info("Updated profile user_id=%s", user_id)
            return profile
        except IntegrityError as exc:
            self._db.rollback()
            logger.warning("Integrity error updating profile user_id=%s: %s", user_id, exc)
            raise DuplicateUsernameError("Username is already taken.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error updating profile user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to update profile.") from exc

    def require_by_user_id(self, user_id: UUID) -> UserProfile:
        """Return a profile or raise :class:`RecordNotFoundError`."""
        profile = self.get_by_user_id(user_id)
        if profile is None:
            raise RecordNotFoundError("Profile not found.")
        return profile

    def list_by_user_ids(self, user_ids: list[UUID]) -> list[UserProfile]:
        """Return profiles for the given user ids."""
        if not user_ids:
            return []
        try:
            stmt = select(UserProfile).where(UserProfile.user_id.in_(user_ids))
            return list(self._db.scalars(stmt).all())
        except SQLAlchemyError as exc:
            logger.error("Database error listing profiles by user ids: %s", exc)
            raise RepositoryError("Failed to list profiles.") from exc

    def list_profiles(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        primary_skill: PrimarySkill | None = None,
        current_status: CurrentStatus | None = None,
        name: str | None = None,
    ) -> tuple[list[UserProfile], int]:
        """Return filtered profiles with total count."""
        from sqlalchemy import func, or_

        try:
            filters = []
            if primary_skill is not None:
                filters.append(UserProfile.primary_skill == primary_skill)
            if current_status is not None:
                filters.append(UserProfile.current_status == current_status)
            if name:
                pattern = f"%{name}%"
                filters.append(
                    or_(
                        UserProfile.first_name.ilike(pattern),
                        UserProfile.last_name.ilike(pattern),
                        UserProfile.username.ilike(pattern),
                    )
                )

            count_stmt = select(func.count()).select_from(UserProfile)
            stmt = select(UserProfile)
            for f in filters:
                count_stmt = count_stmt.where(f)
                stmt = stmt.where(f)

            total = int(self._db.scalar(count_stmt) or 0)
            stmt = (
                stmt.order_by(UserProfile.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            return list(self._db.scalars(stmt).all()), total
        except SQLAlchemyError as exc:
            logger.error("Database error listing profiles: %s", exc)
            raise RepositoryError("Failed to list profiles.") from exc

    def dashboard_status_counts(self) -> dict[str, int]:
        """Count profiles by current_status for the admin dashboard."""
        from sqlalchemy import func

        try:
            rows = self._db.execute(
                select(UserProfile.current_status, func.count())
                .group_by(UserProfile.current_status)
            ).all()
            counts = {
                "students": 0,
                "professionals": 0,
                "job_seekers": 0,
            }
            for status_value, count in rows:
                if status_value == CurrentStatus.STUDENT:
                    counts["students"] = int(count)
                elif status_value == CurrentStatus.WORKING_PROFESSIONAL:
                    counts["professionals"] = int(count)
                elif status_value == CurrentStatus.JOB_SEEKER:
                    counts["job_seekers"] = int(count)
            return counts
        except SQLAlchemyError as exc:
            logger.error("Database error loading profile status counts: %s", exc)
            raise RepositoryError("Failed to load profile status counts.") from exc
