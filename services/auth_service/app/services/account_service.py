"""Account disable, enable, and permanent delete use-case service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.events.account_events import publish_account_deleted
from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.account import (
    AccountStatusResponse,
    DeleteAccountRequest,
    DisableAccountRequest,
    DisableAccountResponse,
    EnableAccountRequest,
    EnableAccountResponse,
)
from app.services.password_service import PasswordService
from sqlalchemy.orm import Session

from shared.exceptions.auth import BlockedUserError, InvalidCredentialsError
from shared.exceptions.base import BusinessException
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)


class AccountService:
    """Own-account disable, enable, and hard-delete orchestration."""

    def __init__(
        self,
        *,
        db: Session,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        email_verification_repository: EmailVerificationRepository,
        password_reset_repository: PasswordResetRepository,
        password_service: PasswordService,
    ) -> None:
        self._db = db
        self._users = user_repository
        self._refresh_tokens = refresh_token_repository
        self._email_verification = email_verification_repository
        self._password_reset = password_reset_repository
        self._passwords = password_service

    def get_status(self, user: User) -> AccountStatusResponse:
        """Return the caller's active / disabled / blocked status."""
        return AccountStatusResponse(
            is_active=user.is_active,
            is_blocked=user.is_blocked,
            disabled_at=user.disabled_at,
            blocked_at=user.blocked_at,
        )

    def disable_account(
        self,
        user: User,
        request: DisableAccountRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> DisableAccountResponse:
        """Disable the caller's account after password confirmation."""
        self._verify_password(user, request.password)

        if user.is_blocked:
            raise BlockedUserError("Your account has been blocked.")

        if not user.is_active:
            raise BusinessException("Account is already disabled.")

        disabled_at = datetime.now(tz=UTC)
        try:
            updated = self._users.update_user(
                user.id,
                commit=False,
                is_active=False,
                disabled_at=disabled_at,
            )
            self._refresh_tokens.revoke_all_tokens(user.id, commit=False)
            self._db.commit()
            self._db.refresh(updated)
        except Exception:
            self._db.rollback()
            raise

        logger.info("Account disabled user_id=%s", user.id)
        self._audit(
            "user_disabled_account",
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        return DisableAccountResponse(
            is_active=False,
            disabled_at=updated.disabled_at,
        )

    def enable_account(
        self,
        request: EnableAccountRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> EnableAccountResponse:
        """Re-enable a self-disabled account using email + password.

        Blocked accounts cannot self-enable — only an admin can unblock.
        """
        user = self._users.get_user_by_email(str(request.email))
        if user is None or not self._passwords.verify(
            request.password, user.password_hash
        ):
            raise InvalidCredentialsError("Invalid email or password.")

        if user.is_blocked:
            raise BlockedUserError(
                "Your account has been blocked. Contact support.",
            )

        if user.is_active:
            raise BusinessException("Account is already active.")

        try:
            updated = self._users.update_user(
                user.id,
                commit=True,
                is_active=True,
                disabled_at=None,
            )
        except Exception:
            self._db.rollback()
            raise

        logger.info("Account enabled user_id=%s", user.id)
        self._audit(
            "user_enabled_account",
            user_id=user.id,
            ip=ip,
            user_agent=user_agent,
        )
        return EnableAccountResponse(
            is_active=True,
            disabled_at=updated.disabled_at,
        )

    def delete_account(
        self,
        user: User,
        request: DeleteAccountRequest,
        *,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Permanently delete the caller's account after password + confirm."""
        if not request.confirm:
            raise BusinessException(
                "Account deletion requires confirm=true.",
            )

        self._verify_password(user, request.password)

        user_id = user.id
        email = user.email

        try:
            self._refresh_tokens.revoke_all_tokens(user_id, commit=False)
            self._email_verification.invalidate_unused_tokens(user_id)
            self._password_reset.invalidate_unused_tokens(user_id)
            self._users.delete_user(user_id)
        except Exception:
            self._db.rollback()
            raise

        publish_account_deleted(user_id, email=email)

        logger.info("Account deleted user_id=%s", user_id)
        self._audit(
            "user_deleted_account",
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
        )

    def _verify_password(self, user: User, password: str) -> None:
        if not self._passwords.verify(password, user.password_hash):
            logger.warning(
                "Account action failed: invalid password user_id=%s",
                user.id,
            )
            raise InvalidCredentialsError("Current password is incorrect.")

    @staticmethod
    def _audit(
        event: str,
        *,
        user_id: UUID,
        ip: str | None,
        user_agent: str | None,
    ) -> None:
        log_security_event(
            event,
            user_id=str(user_id),
            ip=ip or "unknown",
            user_agent=user_agent or "unknown",
            timestamp=datetime.now(tz=UTC).isoformat(),
        )
