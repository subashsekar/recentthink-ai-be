"""Pytest fixtures for CRUD integration tests."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AUTH_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from app.repositories.admin_repository import AdminRepository  # noqa: E402
from app.repositories.email_verification_repository import (  # noqa: E402
    EmailVerificationRepository,
)
from app.repositories.password_reset_repository import PasswordResetRepository  # noqa: E402
from app.repositories.refresh_token_repository import RefreshTokenRepository  # noqa: E402
from app.repositories.user_repository import UserRepository  # noqa: E402

from shared.database import engine  # noqa: E402


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a database session that rolls back all changes after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def admin_repository(db_session: Session) -> AdminRepository:
    """Provide an admin repository bound to the test session."""
    return AdminRepository(db_session)


@pytest.fixture
def user_repository(db_session: Session) -> UserRepository:
    """Provide a user repository bound to the test session."""
    return UserRepository(db_session)


@pytest.fixture
def refresh_token_repository(db_session: Session) -> RefreshTokenRepository:
    """Provide a refresh token repository bound to the test session."""
    return RefreshTokenRepository(db_session)


@pytest.fixture
def email_verification_repository(
    db_session: Session,
) -> EmailVerificationRepository:
    """Provide an email verification repository bound to the test session."""
    return EmailVerificationRepository(db_session)


@pytest.fixture
def password_reset_repository(db_session: Session) -> PasswordResetRepository:
    """Provide a password reset repository bound to the test session."""
    return PasswordResetRepository(db_session)
