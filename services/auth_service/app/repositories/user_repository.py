"""User data-access repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User
from shared.exceptions import DuplicateEmailError, RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for :class:`User` persistence operations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        phone_number: str | None = None,
        is_verified: bool = False,
        is_active: bool = True,
        is_blocked: bool = False,
        total_tokens_used: int = 0,
        total_requests: int = 0,
        last_login: datetime | None = None,
    ) -> User:
        """Persist a new user record."""
        if self.get_user_by_email(email) is not None:
            logger.warning("Duplicate user email on create: %s", email)
            raise DuplicateEmailError(f"User with email '{email}' already exists.")

        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            phone_number=phone_number,
            is_verified=is_verified,
            is_active=is_active,
            is_blocked=is_blocked,
            total_tokens_used=total_tokens_used,
            total_requests=total_requests,
            last_login=last_login,
        )

        try:
            self._db.add(user)
            self._db.commit()
            self._db.refresh(user)
            logger.info("Created user id=%s email=%s", user.id, user.email)
            return user
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Database integrity error creating user: %s", exc)
            raise DuplicateEmailError(
                f"User with email '{email}' already exists.",
            ) from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating user: %s", exc)
            raise RepositoryError("Failed to create user.") from exc

    def get_user_by_id(self, user_id: UUID) -> User | None:
        """Return a user by primary key."""
        try:
            user = self._db.scalar(select(User).where(User.id == user_id))
            if user is not None:
                logger.info("Fetched user id=%s", user_id)
            else:
                logger.info("User not found id=%s", user_id)
            return user
        except SQLAlchemyError as exc:
            logger.error("Database error fetching user id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to fetch user.") from exc

    def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email address."""
        try:
            user = self._db.scalar(select(User).where(User.email == email))
            if user is not None:
                logger.info("Fetched user email=%s", email)
            else:
                logger.info("User not found email=%s", email)
            return user
        except SQLAlchemyError as exc:
            logger.error("Database error fetching user email=%s: %s", email, exc)
            raise RepositoryError("Failed to fetch user.") from exc

    def update_user(self, user_id: UUID, **fields: Any) -> User:
        """Persist changes to an existing user record."""
        user = self.get_user_by_id(user_id)
        if user is None:
            logger.warning("User not found for update id=%s", user_id)
            raise RecordNotFoundError(f"User with id '{user_id}' not found.")

        if "email" in fields and fields["email"] != user.email:
            existing = self.get_user_by_email(fields["email"])
            if existing is not None and existing.id != user_id:
                logger.warning("Duplicate user email on update: %s", fields["email"])
                raise DuplicateEmailError(
                    f"User with email '{fields['email']}' already exists.",
                )

        for key, value in fields.items():
            if hasattr(user, key):
                setattr(user, key, value)

        try:
            self._db.commit()
            self._db.refresh(user)
            logger.info("Updated user id=%s", user_id)
            return user
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Database integrity error updating user id=%s: %s", user_id, exc)
            raise DuplicateEmailError("User email already exists.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error updating user id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to update user.") from exc

    def delete_user(self, user_id: UUID) -> None:
        """Remove a user record."""
        user = self.get_user_by_id(user_id)
        if user is None:
            logger.warning("User not found for delete id=%s", user_id)
            raise RecordNotFoundError(f"User with id '{user_id}' not found.")

        try:
            self._db.delete(user)
            self._db.commit()
            logger.info("Deleted user id=%s", user_id)
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error deleting user id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to delete user.") from exc

    def list_users(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Return a paginated list of user records."""
        try:
            stmt = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
            users = list(self._db.scalars(stmt).all())
            logger.info("Listed users skip=%s limit=%s count=%s", skip, limit, len(users))
            return users
        except SQLAlchemyError as exc:
            logger.error("Database error listing users: %s", exc)
            raise RepositoryError("Failed to list users.") from exc
