"""Refresh token data-access repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.models.refresh_token import RefreshToken
from sqlalchemy import select
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
        token: str,
        expires_at: datetime,
        is_revoked: bool = False,
    ) -> RefreshToken:
        """Persist a new refresh token record."""
        refresh_token = RefreshToken(
            user_id=user_id,
            token=token,
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

    def get_by_token(self, token: str) -> RefreshToken | None:
        """Return a refresh token by its token string."""
        try:
            return self._db.scalar(
                select(RefreshToken).where(RefreshToken.token == token)
            )
        except SQLAlchemyError as exc:
            logger.error("Database error fetching refresh token: %s", exc)
            raise RepositoryError("Failed to fetch refresh token.") from exc

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
