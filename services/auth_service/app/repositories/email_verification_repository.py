"""Email verification token data-access repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.email_verification_token import EmailVerificationToken
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class EmailVerificationRepository:
    """Repository for :class:`EmailVerificationToken` persistence operations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_token(
        self,
        *,
        user_id: UUID,
        token: str,
        expires_at: datetime,
        is_used: bool = False,
    ) -> EmailVerificationToken:
        """Persist a new email verification token record."""
        verification_token = EmailVerificationToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            is_used=is_used,
        )

        try:
            self._db.add(verification_token)
            self._db.commit()
            self._db.refresh(verification_token)
            logger.info(
                "Created email verification token id=%s user_id=%s",
                verification_token.id,
                user_id,
            )
            return verification_token
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Duplicate email verification token: %s", exc)
            raise RepositoryError("Email verification token already exists.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating email verification token: %s", exc)
            raise RepositoryError("Failed to create email verification token.") from exc

    def get_by_id(self, token_id: UUID) -> EmailVerificationToken | None:
        """Return an email verification token by primary key."""
        try:
            return self._db.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.id == token_id
                )
            )
        except SQLAlchemyError as exc:
            logger.error(
                "Database error fetching email verification token id=%s: %s",
                token_id,
                exc,
            )
            raise RepositoryError("Failed to fetch email verification token.") from exc

    def get_by_token(self, token: str) -> EmailVerificationToken | None:
        """Return an email verification token by its token string."""
        try:
            return self._db.scalar(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.token == token
                )
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching email verification token: %s", exc)
            raise RepositoryError("Failed to fetch email verification token.") from exc

    def mark_as_used(self, token_id: UUID) -> EmailVerificationToken:
        """Mark an email verification token as used."""
        verification_token = self.get_by_id(token_id)
        if verification_token is None:
            raise RecordNotFoundError(
                f"Email verification token with id '{token_id}' not found."
            )

        verification_token.is_used = True

        try:
            self._db.commit()
            self._db.refresh(verification_token)
            logger.info("Marked email verification token id=%s as used", token_id)
            return verification_token
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error(
                "Database error updating email verification token id=%s: %s",
                token_id,
                exc,
            )
            raise RepositoryError("Failed to update email verification token.") from exc
