"""Super-admin account seeding on application startup."""

from __future__ import annotations

from app.models.enums import Role
from app.repositories.user_repository import UserRepository
from app.services.password_service import PasswordService
from sqlalchemy.orm import Session

from shared.config import Settings, get_settings
from shared.logging import get_logger

logger = get_logger(__name__)


def _credentials_configured(settings: Settings) -> bool:
    return all(
        (
            settings.super_admin_email,
            settings.super_admin_password,
            settings.super_admin_first_name,
            settings.super_admin_last_name,
        ),
    )


def seed_super_admin(
    db: Session,
    *,
    settings: Settings | None = None,
    password_service: PasswordService | None = None,
    user_repository: UserRepository | None = None,
) -> bool:
    """Create the default super-admin account when one does not already exist.

    Returns ``True`` when a new super-admin was created, ``False`` otherwise.
    Credentials are read from ``Settings``; when any required value is missing
    the seed is skipped without raising.
    """
    cfg = settings or get_settings()
    passwords = password_service or PasswordService()
    users = user_repository or UserRepository(db)

    if users.exists_user_with_role(Role.SUPER_ADMIN):
        logger.info("Super admin already exists; skipping seed.")
        return False

    if not _credentials_configured(cfg):
        logger.warning(
            "Super admin credentials not fully configured; skipping seed.",
        )
        return False

    password_hash = passwords.hash(cfg.super_admin_password)  # type: ignore[arg-type]
    users.create_user(
        first_name=cfg.super_admin_first_name,  # type: ignore[arg-type]
        last_name=cfg.super_admin_last_name,  # type: ignore[arg-type]
        email=cfg.super_admin_email,  # type: ignore[arg-type]
        password_hash=password_hash,
        role=Role.SUPER_ADMIN,
        is_verified=True,
        is_active=True,
    )
    logger.info("Super admin seeded email=%s", cfg.super_admin_email)
    return True
