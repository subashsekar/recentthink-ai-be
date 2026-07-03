"""Password reset token data-access repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.password_reset_token import PasswordResetToken
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class PasswordResetRepository:
    """Repository for :class:`PasswordResetToken` persistence operations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_token(
        self,
        *,
        user_id: UUID,
        token: str,
        expires_at: datetime,
        is_used: bool = False,
    ) -> PasswordResetToken:
        """Persist a new password reset token record."""
        reset_token = PasswordResetToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_used=is_used,
        )

        try:
            self._db.add(reset_token)
            self._db.commit()
            self._db.refresh(reset_token)
            logger.info(
                "Created password reset token id=%s user_id=%s",
                reset_token.id,
                user_id,
            )
            return reset_token
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Duplicate password reset token: %s", exc)
            raise RepositoryError("Password reset token already exists.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating password reset token: %s", exc)
            raise RepositoryError("Failed to create password reset token.") from exc

    def get_by_id(self, token_id: UUID) -> PasswordResetToken | None:
        """Return a password reset token by primary key."""
        try:
            return self._db.scalar(
                select(PasswordResetToken).where(PasswordResetToken.id == token_id)
            )
        except SQLAlchemyError as exc:
            logger.error(
                "Database error fetching password reset token id=%s: %s",
                token_id,
                exc,
            )
            raise RepositoryError("Failed to fetch password reset token.") from exc

    def get_by_token(self, token: str) -> PasswordResetToken | None:
        """Return a password reset token by its token string."""
        try:
            return self._db.scalar(
                select(PasswordResetToken).where(PasswordResetToken.token == token)
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching password reset token: %s", exc)
            raise RepositoryError("Failed to fetch password reset token.") from exc

    def invalidate_unused_tokens(self, user_id: UUID) -> int:
        """Mark every unused reset token for a user as used.

        Called before issuing a fresh token so at most one reset link is
        redeemable per user. Returns the number of tokens invalidated.
        """
        try:
            result = self._db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.is_used.is_(False),
                )
                .values(is_used=True),
            )
            self._db.commit()
            invalidated = result.rowcount or 0
            logger.info(
                "Invalidated %d password reset token(s) user_id=%s",
                invalidated,
                user_id,
            )
            return invalidated
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error(
                "Database error invalidating password reset tokens user_id=%s: %s",
                user_id,
                exc,
            )
            raise RepositoryError(
                "Failed to invalidate password reset tokens.",
            ) from exc

    def consume_token(self, token_id: UUID, *, commit: bool = True) -> bool:
        """Atomically mark a token used only if it is currently unused.

        Uses a conditional ``UPDATE ... WHERE is_used = false`` so that two
        concurrent resets cannot both redeem the same token. Returns ``True``
        when this call consumed the token, ``False`` when it was already used.

        When ``commit`` is ``False`` the change is left pending so the caller
        can commit it as part of a larger atomic transaction.
        """
        try:
            result = self._db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.id == token_id,
                    PasswordResetToken.is_used.is_(False),
                )
                .values(is_used=True),
            )
            if commit:
                self._db.commit()
            consumed = (result.rowcount or 0) == 1
            if consumed:
                logger.info("Consumed password reset token id=%s", token_id)
            else:
                logger.warning(
                    "Password reset token id=%s already consumed", token_id
                )
            return consumed
        except SQLAlchemyError as exc:
            if commit:
                self._db.rollback()
            logger.error(
                "Database error consuming password reset token id=%s: %s",
                token_id,
                exc,
            )
            raise RepositoryError(
                "Failed to consume password reset token.",
            ) from exc

    def mark_as_used(self, token_id: UUID) -> PasswordResetToken:
        """Mark a password reset token as used."""
        reset_token = self.get_by_id(token_id)
        if reset_token is None:
            raise RecordNotFoundError(
                f"Password reset token with id '{token_id}' not found."
            )

        reset_token.is_used = True

        try:
            self._db.commit()
            self._db.refresh(reset_token)
            logger.info("Marked password reset token id=%s as used", token_id)
            return reset_token
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error(
                "Database error updating password reset token id=%s: %s",
                token_id,
                exc,
            )
            raise RepositoryError("Failed to update password reset token.") from exc
