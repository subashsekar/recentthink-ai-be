"""FastAPI dependencies for repository injection."""

from __future__ import annotations

from app.database import get_db
from app.repositories.admin_repository import AdminRepository
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from fastapi import Depends
from sqlalchemy.orm import Session


def get_admin_repository(db: Session = Depends(get_db)) -> AdminRepository:
    """Provide an :class:`AdminRepository` bound to the request session."""
    return AdminRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Provide a :class:`UserRepository` bound to the request session."""
    return UserRepository(db)


def get_refresh_token_repository(
    db: Session = Depends(get_db),
) -> RefreshTokenRepository:
    """Provide a :class:`RefreshTokenRepository` bound to the request session."""
    return RefreshTokenRepository(db)


def get_email_verification_repository(
    db: Session = Depends(get_db),
) -> EmailVerificationRepository:
    """Provide an :class:`EmailVerificationRepository` bound to the request session."""
    return EmailVerificationRepository(db)


def get_password_reset_repository(
    db: Session = Depends(get_db),
) -> PasswordResetRepository:
    """Provide a :class:`PasswordResetRepository` bound to the request session."""
    return PasswordResetRepository(db)
