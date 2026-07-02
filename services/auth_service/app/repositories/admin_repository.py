"""Admin data-access repository."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.admin import Admin
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import DuplicateEmailError, RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class AdminRepository:
    """Repository for :class:`Admin` persistence operations."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create_admin(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        phone_number: str | None = None,
        is_active: bool = True,
    ) -> Admin:
        """Persist a new admin record."""
        if self.get_admin_by_email(email) is not None:
            logger.warning("Duplicate admin email on create: %s", email)
            raise DuplicateEmailError(f"Admin with email '{email}' already exists.")

        admin = Admin(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            is_active=is_active,
        )

        try:
            self._db.add(admin)
            self._db.commit()
            self._db.refresh(admin)
            logger.info("Created admin id=%s email=%s", admin.id, admin.email)
            return admin
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Database integrity error creating admin: %s", exc)
            raise DuplicateEmailError(
                f"Admin with email '{email}' already exists.",
            ) from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error creating admin: %s", exc)
            raise RepositoryError("Failed to create admin.") from exc

    def get_admin_by_id(self, admin_id: UUID) -> Admin | None:
        """Return an admin by primary key."""
        try:
            admin = self._db.scalar(select(Admin).where(Admin.id == admin_id))
            if admin is not None:
                logger.info("Fetched admin id=%s", admin_id)
            else:
                logger.info("Admin not found id=%s", admin_id)
            return admin
        except SQLAlchemyError as exc:
            logger.error("Database error fetching admin id=%s: %s", admin_id, exc)
            raise RepositoryError("Failed to fetch admin.") from exc

    def get_admin_by_email(self, email: str) -> Admin | None:
        """Return an admin by email address."""
        try:
            admin = self._db.scalar(select(Admin).where(Admin.email == email))
            if admin is not None:
                logger.info("Fetched admin email=%s", email)
            else:
                logger.info("Admin not found email=%s", email)
            return admin
        except SQLAlchemyError as exc:
            logger.error("Database error fetching admin email=%s: %s", email, exc)
            raise RepositoryError("Failed to fetch admin.") from exc

    def update_admin(self, admin_id: UUID, **fields: Any) -> Admin:
        """Persist changes to an existing admin record."""
        admin = self.get_admin_by_id(admin_id)
        if admin is None:
            logger.warning("Admin not found for update id=%s", admin_id)
            raise RecordNotFoundError(f"Admin with id '{admin_id}' not found.")

        if "email" in fields and fields["email"] != admin.email:
            existing = self.get_admin_by_email(fields["email"])
            if existing is not None and existing.id != admin_id:
                logger.warning("Duplicate admin email on update: %s", fields["email"])
                raise DuplicateEmailError(
                    f"Admin with email '{fields['email']}' already exists.",
                )

        for key, value in fields.items():
            if hasattr(admin, key):
                setattr(admin, key, value)

        try:
            self._db.commit()
            self._db.refresh(admin)
            logger.info("Updated admin id=%s", admin_id)
            return admin
        except IntegrityError as exc:
            self._db.rollback()
            logger.error(
                "Database integrity error updating admin id=%s: %s", admin_id, exc
            )
            raise DuplicateEmailError(
                "Admin email or phone number already exists."
            ) from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error updating admin id=%s: %s", admin_id, exc)
            raise RepositoryError("Failed to update admin.") from exc

    def delete_admin(self, admin_id: UUID) -> None:
        """Remove an admin record."""
        admin = self.get_admin_by_id(admin_id)
        if admin is None:
            logger.warning("Admin not found for delete id=%s", admin_id)
            raise RecordNotFoundError(f"Admin with id '{admin_id}' not found.")

        try:
            self._db.delete(admin)
            self._db.commit()
            logger.info("Deleted admin id=%s", admin_id)
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Database error deleting admin id=%s: %s", admin_id, exc)
            raise RepositoryError("Failed to delete admin.") from exc

    def list_admins(self, *, skip: int = 0, limit: int = 100) -> list[Admin]:
        """Return a paginated list of admin records."""
        try:
            stmt = (
                select(Admin)
                .order_by(Admin.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            admins = list(self._db.scalars(stmt).all())
            logger.info(
                "Listed admins skip=%s limit=%s count=%s", skip, limit, len(admins)
            )
            return admins
        except SQLAlchemyError as exc:
            logger.error("Database error listing admins: %s", exc)
            raise RepositoryError("Failed to list admins.") from exc
