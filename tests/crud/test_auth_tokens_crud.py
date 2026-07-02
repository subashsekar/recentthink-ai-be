"""Integration tests for authentication token repositories."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken

pytestmark = pytest.mark.db


@pytest.fixture
def user_payload() -> dict[str, str]:
    """Return unique user field values for a single test run."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "first_name": "Token",
        "last_name": "Tester",
        "email": f"token-crud-{suffix}@recentthink.test",
        "password_hash": "hashed-password-placeholder",
    }


@pytest.fixture
def created_user(user_repository: UserRepository, user_payload: dict[str, str]):
    """Persist a user used by token tests."""
    return user_repository.create_user(**user_payload)


def test_refresh_token_create_and_lookup(
    refresh_token_repository: RefreshTokenRepository,
    created_user,
) -> None:
    """Create a refresh token and fetch it by token string."""
    token_value = f"refresh-{uuid.uuid4().hex}"
    expires_at = datetime.now(tz=UTC) + timedelta(days=7)

    created = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token=token_value,
        expires_at=expires_at,
    )

    assert created.id is not None
    assert created.user_id == created_user.id
    assert created.token == token_value
    assert created.is_revoked is False
    assert created.created_at is not None

    fetched = refresh_token_repository.get_by_token(token_value)
    assert fetched is not None
    assert fetched.id == created.id


def test_email_verification_token_create(
    email_verification_repository: EmailVerificationRepository,
    created_user,
) -> None:
    """Create an email verification token linked to a user."""
    token_value = f"verify-{uuid.uuid4().hex}"
    expires_at = datetime.now(tz=UTC) + timedelta(hours=24)

    created = email_verification_repository.create_token(
        user_id=created_user.id,
        token=token_value,
        expires_at=expires_at,
    )

    assert created.user_id == created_user.id
    assert created.token == token_value
    assert created.is_used is False

    fetched = email_verification_repository.get_by_token(token_value)
    assert fetched is not None
    assert fetched.id == created.id


def test_password_reset_token_create(
    password_reset_repository: PasswordResetRepository,
    created_user,
) -> None:
    """Create a password reset token linked to a user."""
    token_value = f"reset-{uuid.uuid4().hex}"
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    created = password_reset_repository.create_token(
        user_id=created_user.id,
        token=token_value,
        expires_at=expires_at,
    )

    assert created.user_id == created_user.id
    assert created.token == token_value
    assert created.is_used is False

    fetched = password_reset_repository.get_by_token(token_value)
    assert fetched is not None
    assert fetched.id == created.id


def test_user_token_relationships(
    db_session: Session,
    user_repository: UserRepository,
    refresh_token_repository: RefreshTokenRepository,
    email_verification_repository: EmailVerificationRepository,
    password_reset_repository: PasswordResetRepository,
    user_payload: dict[str, str],
) -> None:
    """Token records are associated with the owning user via foreign keys."""
    user = user_repository.create_user(**user_payload)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    refresh_token_repository.create_refresh_token(
        user_id=user.id,
        token=f"refresh-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )
    email_verification_repository.create_token(
        user_id=user.id,
        token=f"verify-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )
    password_reset_repository.create_token(
        user_id=user.id,
        token=f"reset-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )

    refresh_count = db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == user.id)
    )
    verify_count = db_session.scalar(
        select(func.count())
        .select_from(EmailVerificationToken)
        .where(EmailVerificationToken.user_id == user.id)
    )
    reset_count = db_session.scalar(
        select(func.count())
        .select_from(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id)
    )

    assert refresh_count == 1
    assert verify_count == 1
    assert reset_count == 1


def test_cascade_delete_removes_tokens(
    db_session: Session,
    user_repository: UserRepository,
    refresh_token_repository: RefreshTokenRepository,
    email_verification_repository: EmailVerificationRepository,
    password_reset_repository: PasswordResetRepository,
    user_payload: dict[str, str],
) -> None:
    """Deleting a user cascades to all related token records."""
    user = user_repository.create_user(**user_payload)
    expires_at = datetime.now(tz=UTC) + timedelta(hours=1)

    refresh_token_repository.create_refresh_token(
        user_id=user.id,
        token=f"refresh-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )
    email_verification_repository.create_token(
        user_id=user.id,
        token=f"verify-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )
    password_reset_repository.create_token(
        user_id=user.id,
        token=f"reset-{uuid.uuid4().hex}",
        expires_at=expires_at,
    )

    user_repository.delete_user(user.id)

    refresh_count = db_session.scalar(
        select(func.count()).select_from(RefreshToken)
    )
    verify_count = db_session.scalar(
        select(func.count()).select_from(EmailVerificationToken)
    )
    reset_count = db_session.scalar(
        select(func.count()).select_from(PasswordResetToken)
    )

    assert refresh_count == 0
    assert verify_count == 0
    assert reset_count == 0
