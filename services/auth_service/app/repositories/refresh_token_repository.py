"""Refresh token data-access repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.models.refresh_token import RefreshToken
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class RefreshTokenRepository:
    """Repository for :class:`RefreshToken` persistence operations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_refresh_token(
        self,
        *,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
        is_revoked: bool = False,
    ) -> RefreshToken:
        """Persist a new refresh token record.

        ``token_hash`` is the SHA-256 digest of the raw token; the raw value is
        never stored. Callers hash the token before persisting it.
        """
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token_hash,
            expires_at=expires_at,
            is_revoked=is_revoked,
        )

        try:
            self._db.add(refresh_token)
            self._db.commit()
            self._db.refresh(refresh_token)
            logger.info("Created refresh token id=%s user_id=%s", refresh_token.id, user_id)
            return refresh_token
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating refresh token: %s", exc)
            raise RepositoryError("Failed to create refresh token.") from exc

    def get_by_id(self, token_id: UUID) -> RefreshToken | None:
        """Return a refresh token by primary key."""
        try:
            return self._db.scalar(
                select(RefreshToken).where(RefreshToken.id == token_id)
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching refresh token id=%s: %s", token_id, exc)
            raise RepositoryError("Failed to fetch refresh token.") from exc

    def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Return a refresh token by the SHA-256 hash of its raw value."""
        try:
            return self._db.scalar(
                select(RefreshToken).where(RefreshToken.token == token_hash)
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching refresh token: %s", exc)
            raise RepositoryError("Failed to fetch refresh token.") from exc

    def rotate_token(
        self,
        *,
        old_token_id: UUID,
        user_id: UUID,
        new_token_hash: str,
        new_expires_at: datetime,
    ) -> RefreshToken:
        """Revoke the current token and persist its replacement atomically.

        Both the revocation of ``old_token_id`` and the insertion of the new
        token are flushed within a single transaction and committed once, so a
        failure rolls back both operations. This guarantees a user never ends
        up with two simultaneously valid refresh tokens.
        """
        old_token = self.get_by_id(old_token_id)
        if old_token is None:
            raise RecordNotFoundError(
                f"Refresh token with id '{old_token_id}' not found."
            )

        new_token = RefreshToken(
            user_id=user_id,
            token=new_token_hash,
            expires_at=new_expires_at,
            is_revoked=False,
        )

        try:
            old_token.is_revoked = True
            self._db.add(new_token)
            self._db.commit()
            self._db.refresh(new_token)
            logger.info(
                "Rotated refresh token old_id=%s new_id=%s user_id=%s",
                old_token_id,
                new_token.id,
                user_id,
            )
            return new_token
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error(
                "Database error rotating refresh token old_id=%s: %s",
                old_token_id,
                exc,
            )
            raise RepositoryError("Failed to rotate refresh token.") from exc

    def revoke_token(self, token_id: UUID) -> RefreshToken:
        """Mark a refresh token as revoked."""
        refresh_token = self.get_by_id(token_id)
        if refresh_token is None:
            raise RecordNotFoundError(f"Refresh token with id '{token_id}' not found.")

        refresh_token.is_revoked = True

        try:
            self._db.commit()
            self._db.refresh(refresh_token)
            logger.info("Revoked refresh token id=%s", token_id)
            return refresh_token
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error revoking refresh token id=%s: %s", token_id, exc)
            raise RepositoryError("Failed to revoke refresh token.") from exc

    def delete_token(self, token_id: UUID) -> None:
        """Remove a refresh token record."""
        refresh_token = self.get_by_id(token_id)
        if refresh_token is None:
            raise RecordNotFoundError(f"Refresh token with id '{token_id}' not found.")

        try:
            self._db.delete(refresh_token)
            self._db.commit()
            logger.info("Deleted refresh token id=%s", token_id)
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error deleting refresh token id=%s: %s", token_id, exc)
            raise RepositoryError("Failed to delete refresh token.") from exc

    def get_active_refresh_tokens(self, user_id: UUID) -> list[RefreshToken]:
        """Return a user's non-revoked, non-expired refresh tokens."""
        now = datetime.now(tz=UTC)
        try:
            stmt = (
                select(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked.is_(False),
                    RefreshToken.expires_at > now,
                )
                .order_by(RefreshToken.created_at.desc())
            )
            return list(self._db.scalars(stmt).all())
        except SQLAlchemyError as exc:
            logger.error(
                "Database error listing active refresh tokens user_id=%s: %s",
                user_id,
                exc,
            )
            raise RepositoryError("Failed to list active refresh tokens.") from exc

    def revoke_all_tokens(self, user_id: UUID) -> int:
        """Revoke every active refresh token for a user.

        Returns the number of tokens revoked.
        """
        try:
            stmt = (
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.is_revoked.is_(False),
                )
                .values(is_revoked=True)
            )
            result = self._db.execute(stmt)
            self._db.commit()
            revoked = result.rowcount or 0
            logger.info("Revoked %s refresh token(s) for user_id=%s", revoked, user_id)
            return revoked
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error(
                "Database error revoking all refresh tokens user_id=%s: %s",
                user_id,
                exc,
            )
            raise RepositoryError("Failed to revoke refresh tokens.") from exc

    def delete_expired_tokens(self) -> int:
        """Delete all refresh tokens whose ``expires_at`` is in the past.

        Returns the number of tokens deleted.
        """
        now = datetime.now(tz=UTC)
        try:
            stmt = delete(RefreshToken).where(RefreshToken.expires_at <= now)
            result = self._db.execute(stmt)
            self._db.commit()
            deleted = result.rowcount or 0
            logger.info("Deleted %s expired refresh token(s)", deleted)
            return deleted
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error deleting expired refresh tokens: %s", exc)
            raise RepositoryError("Failed to delete expired refresh tokens.") from exc
