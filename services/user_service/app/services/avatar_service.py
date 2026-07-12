"""Avatar upload/replace/delete service."""

from __future__ import annotations

import uuid
from pathlib import PurePosixPath
from uuid import UUID

from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import AvatarUploadResponse
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.base import ValidationException
from shared.logging import get_logger
from shared.storage import StorageBackend, StorageError, get_storage

logger = get_logger(__name__)

ADMIN_ROLES = frozenset({"ADMIN", "SUPER_ADMIN"})

_EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class AvatarService:
    """Manage profile picture uploads via the shared storage abstraction."""

    def __init__(
        self,
        db: Session,
        *,
        storage: StorageBackend | None = None,
    ) -> None:
        self._profiles = ProfileRepository(db)
        self._storage = storage or get_storage()
        self._settings = get_settings()

    def upload(
        self,
        *,
        actor_id: UUID,
        actor_role: str,
        target_user_id: UUID,
        data: bytes,
        content_type: str | None,
        filename: str | None = None,
    ) -> AvatarUploadResponse:
        """Upload or replace the avatar for ``target_user_id``."""
        self._assert_can_write(actor_id=actor_id, actor_role=actor_role, target_user_id=target_user_id)
        profile = self._profiles.require_by_user_id(target_user_id)

        normalized_type = (content_type or "").split(";")[0].strip().lower()
        allowed = {t.lower() for t in self._settings.avatar_allowed_content_types}
        if normalized_type not in allowed:
            raise ValidationException(
                "Unsupported avatar format. Allowed: JPEG, PNG, WebP, GIF.",
            )
        if len(data) == 0:
            raise ValidationException("Avatar file is empty.")
        if len(data) > self._settings.avatar_max_bytes:
            max_mb = self._settings.avatar_max_bytes / (1024 * 1024)
            raise ValidationException(f"Avatar exceeds maximum size of {max_mb:.0f} MiB.")

        extension = _EXT_BY_CONTENT_TYPE.get(normalized_type)
        if extension is None and filename:
            extension = PurePosixPath(filename).suffix.lower() or ".bin"
        if not extension:
            extension = ".bin"

        key = f"avatars/{target_user_id}/{uuid.uuid4().hex}{extension}"
        previous_url = profile.profile_picture_url

        try:
            url = self._storage.save(key=key, data=data, content_type=normalized_type)
        except StorageError as exc:
            raise ValidationException("Failed to store avatar.") from exc

        updated = self._profiles.update_profile(
            target_user_id,
            profile_picture_url=url,
        )
        if previous_url:
            self._safe_delete_url(previous_url)

        logger.info("Avatar uploaded user_id=%s", target_user_id)
        return AvatarUploadResponse(profile_picture_url=updated.profile_picture_url or url)

    def delete(
        self,
        *,
        actor_id: UUID,
        actor_role: str,
        target_user_id: UUID,
    ) -> None:
        """Delete the avatar for ``target_user_id``."""
        self._assert_can_write(actor_id=actor_id, actor_role=actor_role, target_user_id=target_user_id)
        profile = self._profiles.require_by_user_id(target_user_id)
        previous_url = profile.profile_picture_url
        if not previous_url:
            return
        self._profiles.update_profile(target_user_id, profile_picture_url=None)
        self._safe_delete_url(previous_url)
        logger.info("Avatar deleted user_id=%s", target_user_id)

    def _safe_delete_url(self, url: str) -> None:
        """Best-effort delete of a previously stored object."""
        prefix = self._settings.storage_public_base_url.rstrip("/") + "/"
        if not url.startswith(prefix):
            return
        key = url[len(prefix) :]
        try:
            self._storage.delete(key)
        except StorageError:
            logger.warning("Failed to delete previous avatar object key=%s", key)

    @staticmethod
    def _assert_can_write(*, actor_id: UUID, actor_role: str, target_user_id: UUID) -> None:
        if actor_id == target_user_id or actor_role in ADMIN_ROLES:
            return
        raise ForbiddenError("You do not have permission to modify this avatar.")
