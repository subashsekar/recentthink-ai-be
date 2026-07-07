"""Pytest fixtures for CRUD integration tests."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.repositories.admin_repository import AdminRepository
    from app.repositories.email_verification_repository import (
        EmailVerificationRepository,
    )
    from app.repositories.password_reset_repository import PasswordResetRepository
    from app.repositories.refresh_token_repository import RefreshTokenRepository
    from app.repositories.user_repository import UserRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AUTH_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from shared.database import engine  # noqa: E402


def _user_repository(session: Session) -> UserRepository:
    from app.repositories.user_repository import UserRepository

    return UserRepository(session)


def _admin_repository(session: Session) -> AdminRepository:
    from app.repositories.admin_repository import AdminRepository

    return AdminRepository(session)


def _refresh_token_repository(session: Session) -> RefreshTokenRepository:
    from app.repositories.refresh_token_repository import RefreshTokenRepository

    return RefreshTokenRepository(session)


def _email_verification_repository(session: Session) -> EmailVerificationRepository:
    from app.repositories.email_verification_repository import (
        EmailVerificationRepository,
    )

    return EmailVerificationRepository(session)


def _password_reset_repository(session: Session) -> PasswordResetRepository:
    from app.repositories.password_reset_repository import PasswordResetRepository

    return PasswordResetRepository(session)


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a database session that rolls back all changes after each test.

    ``join_transaction_mode="create_savepoint"`` makes the code under test
    commit to a SAVEPOINT rather than the real transaction, so the outer
    ``transaction.rollback()`` reliably undoes everything and tests never
    pollute the database.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def admin_repository(db_session: Session) -> AdminRepository:
    """Provide an admin repository bound to the test session."""
    return _admin_repository(db_session)


@pytest.fixture
def user_repository(db_session: Session) -> UserRepository:
    """Provide a user repository bound to the test session."""
    return _user_repository(db_session)


@pytest.fixture
def refresh_token_repository(db_session: Session) -> RefreshTokenRepository:
    """Provide a refresh token repository bound to the test session."""
    return _refresh_token_repository(db_session)


@pytest.fixture
def email_verification_repository(
    db_session: Session,
) -> EmailVerificationRepository:
    """Provide an email verification repository bound to the test session."""
    return _email_verification_repository(db_session)


@pytest.fixture
def password_reset_repository(db_session: Session) -> PasswordResetRepository:
    """Provide a password reset repository bound to the test session."""
    return _password_reset_repository(db_session)
