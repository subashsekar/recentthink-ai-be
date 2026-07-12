"""User data-access repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.models.enums import Role
from app.models.user import User
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import DuplicateEmailError, RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class UserRepository:
    """Repository for :class:`User` persistence operations."""

    # Columns a caller is allowed to modify through :meth:`update_user`.
    # Excludes ``id`` and the timestamp columns, which are managed by the ORM.
    EDITABLE_FIELDS: frozenset[str] = frozenset(
        {
            "first_name",
            "last_name",
            "email",
            "password_hash",
            "password_changed_at",
            "role",
            "is_verified",
            "email_verified_at",
            "is_active",
            "disabled_at",
            "is_blocked",
            "blocked_at",
            "blocked_reason",
            "deleted_at",
        }
    )

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_user(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        role: Role = Role.USER,
        is_verified: bool = False,
        is_active: bool = True,
    ) -> User:
        """Persist a new user record."""
        if self.get_user_by_email(email) is not None:
            logger.warning("Duplicate user email on create: %s", email)
            raise DuplicateEmailError(f"User with email '{email}' already exists.")

        user = User(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
            role=role,
            is_verified=is_verified,
            is_active=is_active,
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
            return self._db.scalar(select(User).where(User.id == user_id))
        except SQLAlchemyError as exc:
            logger.error("Database error fetching user id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to fetch user.") from exc

    def get_user_by_email(self, email: str) -> User | None:
        """Return a user by email address."""
        try:
            return self._db.scalar(select(User).where(User.email == email))
        except SQLAlchemyError as exc:
            logger.error("Database error fetching user email=%s: %s", email, exc)
            raise RepositoryError("Failed to fetch user.") from exc

    def exists_user_with_role(self, role: Role) -> bool:
        """Return ``True`` when at least one user has the given role."""
        try:
            count = self._db.scalar(
                text("SELECT COUNT(*) FROM users WHERE role = :role"),
                {"role": role.value},
            )
            return bool(count)
        except SQLAlchemyError as exc:
            logger.error("Database error checking role=%s existence: %s", role, exc)
            raise RepositoryError("Failed to check user role.") from exc

    def update_user(self, user_id: UUID, *, commit: bool = True, **fields: Any) -> User:
        """Persist changes to an existing user record.

        Only whitelisted columns (:attr:`EDITABLE_FIELDS`) may be updated;
        passing any other key raises :class:`ValueError` so that non-editable
        or unknown attributes cannot be silently written.

        When ``commit`` is ``False`` the changes are flushed but not committed,
        allowing the caller to coordinate a single, atomic transaction across
        multiple repositories that share the session.
        """
        unknown = set(fields) - self.EDITABLE_FIELDS
        if unknown:
            raise ValueError(
                f"Cannot update non-editable field(s): {sorted(unknown)}"
            )

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
            setattr(user, key, value)

        try:
            self._db.flush()
            if commit:
                self._db.commit()
                self._db.refresh(user)
            logger.info("Updated user id=%s", user_id)
            return user
        except IntegrityError as exc:
            if commit:
                self._db.rollback()
            logger.error(
                "Database integrity error updating user id=%s: %s", user_id, exc
            )
            raise DuplicateEmailError("User email already exists.") from exc
        except SQLAlchemyError as exc:
            if commit:
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

    def list_users(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        name: str | None = None,
        email: str | None = None,
        role: Role | None = None,
        is_verified: bool | None = None,
        is_blocked: bool | None = None,
        is_active: bool | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[User], int]:
        """Return a filtered, paginated list of users and the total match count."""
        try:
            filters: list[Any] = []
            if name:
                pattern = f"%{name}%"
                filters.append(
                    or_(
                        User.first_name.ilike(pattern),
                        User.last_name.ilike(pattern),
                        func.concat(User.first_name, " ", User.last_name).ilike(pattern),
                    )
                )
            if email:
                filters.append(User.email.ilike(f"%{email}%"))
            if role is not None:
                filters.append(User.role == role)
            if is_verified is not None:
                filters.append(User.is_verified.is_(is_verified))
            if is_blocked is not None:
                filters.append(User.is_blocked.is_(is_blocked))
            if is_active is not None:
                filters.append(User.is_active.is_(is_active))
            if created_from is not None:
                filters.append(User.created_at >= created_from)
            if created_to is not None:
                filters.append(User.created_at <= created_to)

            where_clause = and_(*filters) if filters else None

            count_stmt = select(func.count()).select_from(User)
            if where_clause is not None:
                count_stmt = count_stmt.where(where_clause)
            total = int(self._db.scalar(count_stmt) or 0)

            sort_column = {
                "created_at": User.created_at,
                "email": User.email,
                "first_name": User.first_name,
                "last_name": User.last_name,
                "role": User.role,
            }.get(sort, User.created_at)
            ordering = (
                sort_column.desc() if order.lower() == "desc" else sort_column.asc()
            )

            stmt = select(User)
            if where_clause is not None:
                stmt = stmt.where(where_clause)
            stmt = stmt.order_by(ordering).offset(skip).limit(limit)
            return list(self._db.scalars(stmt).all()), total
        except SQLAlchemyError as exc:
            logger.error("Database error listing users: %s", exc)
            raise RepositoryError("Failed to list users.") from exc

    def list_all_user_ids(self) -> list[UUID]:
        """Return every user id (for admin broadcast fan-out)."""
        try:
            return list(self._db.scalars(select(User.id)).all())
        except SQLAlchemyError as exc:
            logger.error("Database error listing user ids: %s", exc)
            raise RepositoryError("Failed to list user ids.") from exc

    def dashboard_counts(self, *, today_start: datetime) -> dict[str, int]:
        """Return identity-level dashboard counters."""
        try:
            row = self._db.execute(
                select(
                    func.count().label("total_users"),
                    func.count().filter(User.is_active.is_(True)).label("active_users"),
                    func.count()
                    .filter(User.created_at >= today_start)
                    .label("new_users_today"),
                    func.count()
                    .filter(User.is_verified.is_(True))
                    .label("verified_users"),
                    func.count()
                    .filter(User.is_blocked.is_(True))
                    .label("blocked_users"),
                ).select_from(User)
            ).one()
            return {
                "total_users": int(row.total_users or 0),
                "active_users": int(row.active_users or 0),
                "new_users_today": int(row.new_users_today or 0),
                "verified_users": int(row.verified_users or 0),
                "blocked_users": int(row.blocked_users or 0),
            }
        except SQLAlchemyError as exc:
            logger.error("Database error loading dashboard counts: %s", exc)
            raise RepositoryError("Failed to load dashboard counts.") from exc
