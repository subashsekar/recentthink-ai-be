"""Password reset use-case service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.security.tokens import hash_token
from app.services.email.base import EmailService
from app.services.email.templates import build_password_reset_email
from app.services.one_time_token_validation import validate_one_time_token
from app.services.password_service import PasswordService
from sqlalchemy.orm import Session

from shared.config import Settings, get_settings
from shared.exceptions.auth import UsedTokenError, UserNotFoundError
from shared.exceptions.email import EmailDeliveryError
from shared.logging import get_logger

logger = get_logger(__name__)

_TOKEN_ENTROPY_BYTES = 32


class PasswordResetService:
    """Orchestrates forgot-password requests and password resets.

    Reset tokens are high-entropy random strings. Only their SHA-256 digest is
    persisted; the raw token is delivered solely via email.
    """

    def __init__(
        self,
        *,
        db: Session,
        user_repository: UserRepository,
        password_reset_repository: PasswordResetRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_service: PasswordService,
        email_service: EmailService,
        settings: Settings | None = None,
    ) -> None:
        self._db = db
        self._users = user_repository
        self._tokens = password_reset_repository
        self._refresh_tokens = refresh_token_repository
        self._passwords = password_service
        self._email = email_service
        self._settings = settings or get_settings()

    def _generate_raw_token(self) -> str:
        return secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)

    def _token_expiry(self) -> datetime:
        return datetime.now(tz=UTC) + timedelta(
            hours=self._settings.password_reset_token_expire_hours,
        )

    def _build_reset_link(self, raw_token: str) -> str:
        base = self._settings.password_reset_url
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{urlencode({'token': raw_token})}"

    def _send_reset_email(self, user: User) -> None:
        raw_token = self._generate_raw_token()
        self._tokens.create_token(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=self._token_expiry(),
        )

        message = build_password_reset_email(
            to_email=user.email,
            recipient_name=user.first_name,
            reset_link=self._build_reset_link(raw_token),
            expire_hours=self._settings.password_reset_token_expire_hours,
            app_name=self._settings.app_name,
            support_email=self._settings.email_support_address,
        )
        self._email.send_email(message)

    def request_password_reset(self, email: str) -> None:
        """Issue a password reset email when the account exists.

        Always completes without error to avoid email enumeration. Prior unused
        reset tokens for the user are invalidated before a new one is issued.
        """
        user = self._users.get_user_by_email(email)
        if user is None:
            # Perform comparable throwaway work so the response does not return
            # noticeably faster for unknown emails (a coarse timing-enumeration
            # mitigation; the definitive fix is async email delivery / gateway
            # rate limiting).
            self._generate_raw_token()
            logger.info("Password reset requested for unknown email")
            return

        logger.info("Password reset requested user_id=%s", user.id)
        self._tokens.invalidate_unused_tokens(user.id)

        try:
            self._send_reset_email(user)
            logger.info("Password reset email sent user_id=%s", user.id)
        except EmailDeliveryError:
            logger.exception(
                "Password reset email delivery failed user_id=%s",
                user.id,
            )

    def reset_password(self, raw_token: str, new_password: str) -> None:
        """Validate a reset token, update the password, and revoke sessions.

        The token consumption, password update, and refresh-token revocation
        are committed as a single atomic transaction so a partial failure can
        never leave the password changed while the token stays reusable (or the
        sessions un-revoked). The token is consumed with a conditional update so
        concurrent requests cannot both redeem it.
        """
        stored = validate_one_time_token(
            self._tokens.get_by_token(hash_token(raw_token)),
            log_context="Password reset",
            invalid_message="Invalid password reset token.",
            used_message="This password reset link has already been used.",
            expired_message="This password reset link has expired.",
        )

        user = self._users.get_user_by_id(stored.user_id)
        if user is None:
            logger.warning(
                "Password reset failed: user not found id=%s",
                stored.user_id,
            )
            raise UserNotFoundError("User not found.")

        password_hash = self._passwords.hash(new_password)
        changed_at = datetime.now(tz=UTC)
        try:
            if not self._tokens.consume_token(stored.id, commit=False):
                # Lost the race to a concurrent reset that already redeemed it.
                raise UsedTokenError(
                    "This password reset link has already been used.",
                )
            self._users.update_user(
                user.id,
                commit=False,
                password_hash=password_hash,
                password_changed_at=changed_at,
            )
            self._refresh_tokens.revoke_all_tokens(user.id, commit=False)
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        logger.info("Password successfully reset user_id=%s", user.id)
