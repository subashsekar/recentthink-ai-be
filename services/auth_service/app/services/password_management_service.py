"""Authenticated password change use-case service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.security.tokens import hash_token
from app.services.password_service import PasswordService
from sqlalchemy.orm import Session

from shared.config import Settings, get_settings
from shared.exceptions.auth import InvalidCredentialsError, PasswordReuseError
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


class PasswordManagementService:
    """Handles password changes for authenticated users."""

    def __init__(
        self,
        *,
        db: Session,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_service: PasswordService,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._passwords = password_service
        self._settings = settings or get_settings()

    def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        refresh_token: str | None = None,
    ) -> None:
        """Update the user's password and revoke other active sessions."""
        if not self._passwords.verify(current_password, user.password_hash):
            logger.warning("Password change failed: invalid current password user_id=%s", user.id)
            raise InvalidCredentialsError("Current password is incorrect.")

        if self._passwords.verify(new_password, user.password_hash):
            logger.warning("Password change failed: password reuse user_id=%s", user.id)
            raise PasswordReuseError(
                "New password must be different from your current password.",
            )

        password_hash = self._passwords.hash(new_password)
        changed_at = datetime.now(tz=UTC)
        try:
            self._users.update_user(
                user.id,
                commit=False,
                password_hash=password_hash,
                password_changed_at=changed_at,
            )
            self._revoke_sessions(user.id, refresh_token=refresh_token)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        logger.info("Password changed user_id=%s", user.id)
        log_security_event("password_change", user_id=str(user.id))

    def _revoke_sessions(self, user_id: UUID, *, refresh_token: str | None) -> None:
        if (
            self._settings.change_password_keep_current_session
            and refresh_token is not None
        ):
            keep_hash = hash_token(refresh_token)
            stored = self._refresh_tokens.get_by_token_hash(keep_hash)
            if stored is not None and stored.user_id == user_id and not stored.is_revoked:
                self._refresh_tokens.revoke_all_tokens_except(
                    user_id,
                    keep_token_hash=keep_hash,
                    commit=False,
                )
                return

        self._refresh_tokens.revoke_all_tokens(user_id, commit=False)
