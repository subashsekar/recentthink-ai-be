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
    """Create a refresh token (stored as a hash) and fetch it by hash."""
    token_hash = f"hash-{uuid.uuid4().hex}"
    expires_at = datetime.now(tz=UTC) + timedelta(days=7)

    created = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    assert created.id is not None
    assert created.user_id == created_user.id
    assert created.token == token_hash
    assert created.is_revoked is False
    assert created.created_at is not None

    fetched = refresh_token_repository.get_by_token_hash(token_hash)
    assert fetched is not None
    assert fetched.id == created.id


def test_refresh_token_rotation_is_atomic(
    refresh_token_repository: RefreshTokenRepository,
    created_user,
) -> None:
    """Rotation revokes the old token and creates the new one in one commit."""
    now = datetime.now(tz=UTC)
    old = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"old-{uuid.uuid4().hex}",
        expires_at=now + timedelta(days=7),
    )
    new_hash = f"new-{uuid.uuid4().hex}"

    new_token = refresh_token_repository.rotate_token(
        old_token_id=old.id,
        user_id=created_user.id,
        new_token_hash=new_hash,
        new_expires_at=now + timedelta(days=7),
    )

    refreshed_old = refresh_token_repository.get_by_id(old.id)
    assert refreshed_old is not None
    assert refreshed_old.is_revoked is True
    assert new_token.is_revoked is False
    assert refresh_token_repository.get_by_token_hash(new_hash) is not None


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
        token_hash=f"refresh-{uuid.uuid4().hex}",
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


def test_get_active_refresh_tokens_excludes_revoked_and_expired(
    refresh_token_repository: RefreshTokenRepository,
    created_user,
) -> None:
    """Only non-revoked, non-expired tokens are returned as active."""
    now = datetime.now(tz=UTC)

    active = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"active-{uuid.uuid4().hex}",
        expires_at=now + timedelta(days=7),
    )
    revoked = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"revoked-{uuid.uuid4().hex}",
        expires_at=now + timedelta(days=7),
    )
    refresh_token_repository.revoke_token(revoked.id)
    refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"expired-{uuid.uuid4().hex}",
        expires_at=now - timedelta(days=1),
    )

    active_tokens = refresh_token_repository.get_active_refresh_tokens(
        created_user.id
    )
    active_ids = {token.id for token in active_tokens}

    assert active.id in active_ids
    assert revoked.id not in active_ids
    assert len(active_tokens) == 1


def test_revoke_all_tokens(
    refresh_token_repository: RefreshTokenRepository,
    created_user,
) -> None:
    """Revoking all tokens marks every active token as revoked."""
    now = datetime.now(tz=UTC)
    for _ in range(3):
        refresh_token_repository.create_refresh_token(
            user_id=created_user.id,
            token_hash=f"refresh-{uuid.uuid4().hex}",
            expires_at=now + timedelta(days=7),
        )

    revoked_count = refresh_token_repository.revoke_all_tokens(created_user.id)

    assert revoked_count == 3
    assert refresh_token_repository.get_active_refresh_tokens(created_user.id) == []


def test_delete_expired_tokens(
    db_session: Session,
    refresh_token_repository: RefreshTokenRepository,
    created_user,
) -> None:
    """Expired tokens are deleted; valid tokens are retained."""
    now = datetime.now(tz=UTC)
    valid = refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"valid-{uuid.uuid4().hex}",
        expires_at=now + timedelta(days=7),
    )
    refresh_token_repository.create_refresh_token(
        user_id=created_user.id,
        token_hash=f"expired-{uuid.uuid4().hex}",
        expires_at=now - timedelta(days=1),
    )

    deleted_count = refresh_token_repository.delete_expired_tokens()

    assert deleted_count >= 1
    assert refresh_token_repository.get_by_id(valid.id) is not None


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
        token_hash=f"refresh-{uuid.uuid4().hex}",
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

    assert refresh_count == 0
    assert verify_count == 0
    assert reset_count == 0
