"""Email verification use-case service."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.user_repository import UserRepository
from app.security.tokens import hash_token
from app.services.email.base import EmailService
from app.services.email.templates import build_verification_email
from app.services.one_time_token_validation import validate_one_time_token

from shared.config import Settings, get_settings
from shared.exceptions.auth import (
    EmailAlreadyVerifiedError,
    UserNotFoundError,
)
from shared.logging import get_logger
from shared.logging.security import log_security_event

logger = get_logger(__name__)

# Bytes of entropy for verification tokens. 32 bytes (256 bits) yields a
# ~43-char URL-safe string, matching the refresh-token strength.
_TOKEN_ENTROPY_BYTES = 32


class EmailVerificationService:
    """Orchestrates issuing, verifying, and resending email verification tokens.

    Tokens are high-entropy random strings. Only their SHA-256 digest is
    persisted (never the raw value), so a database compromise cannot reveal a
    usable verification link. The raw token is delivered solely via email.
    """

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        email_verification_repository: EmailVerificationRepository,
        email_service: EmailService,
        settings: Settings | None = None,
    ) -> None:
        self._users = user_repository
        self._tokens = email_verification_repository
        self._email = email_service
        self._settings = settings or get_settings()

    def _generate_raw_token(self) -> str:
        """Return a fresh cryptographically secure opaque token."""
        return secrets.token_urlsafe(_TOKEN_ENTROPY_BYTES)

    def _token_expiry(self) -> datetime:
        return datetime.now(tz=UTC) + timedelta(
            hours=self._settings.email_verification_token_expire_hours,
        )

    def _build_verification_link(self, raw_token: str) -> str:
        base = self._settings.email_verification_url
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}{urlencode({'token': raw_token})}"

    def send_verification_email(self, user: User) -> None:
        """Issue a new verification token for ``user`` and email the link.

        The raw token is stored only as a hash and embedded in the emailed
        link. Raises :class:`shared.exceptions.email.EmailDeliveryError` if the
        transport fails.
        """
        raw_token = self._generate_raw_token()
        self._tokens.create_token(
            user_id=user.id,
            token=hash_token(raw_token),
            expires_at=self._token_expiry(),
        )

        message = build_verification_email(
            to_email=user.email,
            recipient_name=user.first_name,
            verification_link=self._build_verification_link(raw_token),
            expire_hours=self._settings.email_verification_token_expire_hours,
            app_name=self._settings.app_name,
            support_email=self._settings.email_support_address,
        )
        self._email.send_email(message)
        logger.info("Verification email sent user_id=%s", user.id)

    def verify_email(self, raw_token: str) -> User:
        """Validate a verification token and mark the account as verified.

        Enforces expiry and one-time use, then flips ``is_verified`` and
        consumes the token. Idempotent for the user flag but the token can only
        be redeemed once.
        """
        stored = validate_one_time_token(
            self._tokens.get_by_token(hash_token(raw_token)),
            log_context="Email verification",
            invalid_message="Invalid verification token.",
            used_message="This verification link has already been used.",
            expired_message="This verification link has expired.",
        )

        user = self._users.get_user_by_id(stored.user_id)
        if user is None:
            logger.warning(
                "Email verification failed: user not found id=%s",
                stored.user_id,
            )
            raise UserNotFoundError("User not found.")

        if not user.is_verified:
            self._users.update_user(user.id, is_verified=True)
        self._tokens.mark_as_used(stored.id)

        logger.info("Email verified user_id=%s", user.id)
        log_security_event("email_verification", user_id=str(user.id))
        return user

    def resend_verification(self, email: str) -> None:
        """Reissue a verification email, invalidating prior unused tokens.

        Raises :class:`UserNotFoundError` when no account exists and
        :class:`EmailAlreadyVerifiedError` when the account is already verified.
        """
        user = self._users.get_user_by_email(email)
        if user is None:
            logger.warning("Resend verification failed: user not found")
            raise UserNotFoundError("User not found.")

        if user.is_verified:
            logger.info("Resend verification skipped: already verified user_id=%s", user.id)
            raise EmailAlreadyVerifiedError("Email address is already verified.")

        self._tokens.invalidate_unused_tokens(user.id)
        self.send_verification_email(user)
        logger.info("Verification email resent user_id=%s", user.id)
