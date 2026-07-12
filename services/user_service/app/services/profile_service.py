"""Profile business logic."""

from __future__ import annotations

from uuid import UUID

from app.models.profile import UserProfile
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileCreate, ProfileUpdate
from sqlalchemy.orm import Session

from shared.exceptions.auth import ForbiddenError
from shared.logging import get_logger

logger = get_logger(__name__)

ADMIN_ROLES = frozenset({"ADMIN", "SUPER_ADMIN"})


class ProfileService:
    """Own-profile and admin profile management."""

    def __init__(self, db: Session) -> None:
        self._profiles = ProfileRepository(db)

    def get_profile(self, *, actor_id: UUID, actor_role: str, target_user_id: UUID) -> UserProfile:
        """Return a profile when the actor is the owner or an admin."""
        self._assert_can_read(actor_id=actor_id, actor_role=actor_role, target_user_id=target_user_id)
        return self._profiles.require_by_user_id(target_user_id)

    def create_profile(self, *, user_id: UUID, payload: ProfileCreate) -> UserProfile:
        """Create a profile for ``user_id``."""
        data = payload.model_dump(exclude_unset=True)
        profile = self._profiles.create_profile(user_id=user_id, **data)
        logger.info("Profile created user_id=%s", user_id)
        return profile

    def update_profile(
        self,
        *,
        actor_id: UUID,
        actor_role: str,
        target_user_id: UUID,
        payload: ProfileUpdate,
    ) -> UserProfile:
        """Update a profile when the actor is the owner or an admin.

        Creates the profile on first update if it does not yet exist.
        """
        self._assert_can_write(
            actor_id=actor_id,
            actor_role=actor_role,
            target_user_id=target_user_id,
        )
        data = payload.model_dump(exclude_unset=True)
        existing = self._profiles.get_by_user_id(target_user_id)
        if existing is None:
            create_payload = ProfileCreate.model_validate(data)
            profile = self.create_profile(user_id=target_user_id, payload=create_payload)
            logger.info("Profile created via update user_id=%s", target_user_id)
            return profile
        profile = self._profiles.update_profile(target_user_id, **data)
        logger.info("Profile updated user_id=%s", target_user_id)
        return profile

    @staticmethod
    def _assert_can_read(*, actor_id: UUID, actor_role: str, target_user_id: UUID) -> None:
        if actor_id == target_user_id or actor_role in ADMIN_ROLES:
            return
        raise ForbiddenError("You do not have permission to view this profile.")

    @staticmethod
    def _assert_can_write(*, actor_id: UUID, actor_role: str, target_user_id: UUID) -> None:
        if actor_id == target_user_id or actor_role in ADMIN_ROLES:
            return
        raise ForbiddenError("You do not have permission to update this profile.")
