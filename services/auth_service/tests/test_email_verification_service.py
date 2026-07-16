"""Unit tests for EmailVerificationService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.security.tokens import hash_token
from app.services.email.base import EmailService
from app.services.email_verification_service import EmailVerificationService
from shared.config import Settings
from shared.exceptions.auth import (
    EmailAlreadyVerifiedError,
    ExpiredTokenError,
    InvalidTokenError,
    UsedTokenError,
    UserNotFoundError,
)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        app_name="RecentThink",
        email_support_address="support@example.com",
        email_verification_url="https://app.example.com/verify",
        email_verification_token_expire_hours=24,
    )


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def token_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def email_service() -> MagicMock:
    return MagicMock(spec=EmailService)


@pytest.fixture
def verification_service(
    user_repository: MagicMock,
    token_repository: MagicMock,
    email_service: MagicMock,
    settings: Settings,
) -> EmailVerificationService:
    return EmailVerificationService(
        user_repository=user_repository,
        email_verification_repository=token_repository,
        email_service=email_service,
        settings=settings,
    )


def _make_user(*, is_verified: bool = False) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Jane"
    user.email = "user@example.com"
    user.is_verified = is_verified
    return user


def _make_token(
    *,
    user_id: object,
    is_used: bool = False,
    expires_at: datetime | None = None,
) -> MagicMock:
    stored = MagicMock()
    stored.id = uuid4()
    stored.user_id = user_id
    stored.is_used = is_used
    stored.expires_at = expires_at or (datetime.now(tz=UTC) + timedelta(hours=1))
    return stored


def test_send_verification_email_stores_hashed_token(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user = _make_user()

    verification_service.send_verification_email(user)

    token_repository.create_token.assert_called_once()
    stored_token = token_repository.create_token.call_args.kwargs["token"]
    # The persisted value must be a SHA-256 digest, never the raw token.
    assert len(stored_token) == 64
    email_service.send_email.assert_called_once()


def test_send_verification_email_link_matches_stored_hash(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user = _make_user()

    verification_service.send_verification_email(user)

    stored_hash = token_repository.create_token.call_args.kwargs["token"]
    message = email_service.send_email.call_args.args[0]
    # Extract the raw token from the emitted link and confirm hashing it yields
    # exactly what was stored — i.e. the raw token is never persisted.
    raw_token = message.html_body.split("token=")[1].split('"')[0].split("&")[0]
    assert hash_token(raw_token) == stored_hash


def test_generated_tokens_are_unique(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
) -> None:
    user = _make_user()

    verification_service.send_verification_email(user)
    first = token_repository.create_token.call_args.kwargs["token"]
    verification_service.send_verification_email(user)
    second = token_repository.create_token.call_args.kwargs["token"]

    assert first != second


def test_verify_email_success(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user(is_verified=False)
    stored = _make_token(user_id=user.id)
    token_repository.get_by_token.return_value = stored
    user_repository.get_user_by_id.return_value = user

    result = verification_service.verify_email("raw-token")

    assert result is user
    user_repository.update_user.assert_called_once()
    update_kwargs = user_repository.update_user.call_args.kwargs
    assert update_kwargs["is_verified"] is True
    assert update_kwargs["email_verified_at"] is not None
    token_repository.mark_as_used.assert_called_once_with(stored.id)


def test_verify_email_looks_up_by_hash_not_raw(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user()
    token_repository.get_by_token.return_value = _make_token(user_id=user.id)
    user_repository.get_user_by_id.return_value = user

    verification_service.verify_email("raw-token")

    lookup_arg = token_repository.get_by_token.call_args.args[0]
    assert lookup_arg != "raw-token"
    assert lookup_arg == hash_token("raw-token")


def test_verify_email_invalid_token(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = None

    with pytest.raises(InvalidTokenError):
        verification_service.verify_email("missing")


def test_verify_email_used_token(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(
        user_id=uuid4(),
        is_used=True,
    )

    with pytest.raises(UsedTokenError):
        verification_service.verify_email("used")


def test_verify_email_expired_token(
    verification_service: EmailVerificationService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) - timedelta(hours=1),
    )

    with pytest.raises(ExpiredTokenError):
        verification_service.verify_email("expired")


def test_verify_email_naive_expiry_treated_as_utc(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user()
    token_repository.get_by_token.return_value = _make_token(
        user_id=user.id,
        expires_at=datetime.now() + timedelta(hours=1),  # noqa: DTZ005
    )
    user_repository.get_user_by_id.return_value = user

    result = verification_service.verify_email("naive")

    assert result is user


def test_verify_email_user_not_found(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(user_id=uuid4())
    user_repository.get_user_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        verification_service.verify_email("orphan")


def test_verify_email_already_verified_user_is_idempotent(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user(is_verified=True)
    stored = _make_token(user_id=user.id)
    token_repository.get_by_token.return_value = stored
    user_repository.get_user_by_id.return_value = user

    verification_service.verify_email("raw-token")

    # Already verified: no redundant update, but the token is still consumed.
    user_repository.update_user.assert_not_called()
    token_repository.mark_as_used.assert_called_once_with(stored.id)


def test_resend_verification_invalidates_and_sends(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user = _make_user(is_verified=False)
    user_repository.get_user_by_email.return_value = user

    verification_service.resend_verification("user@example.com")

    token_repository.invalidate_unused_tokens.assert_called_once_with(user.id)
    token_repository.create_token.assert_called_once()
    email_service.send_email.assert_called_once()


def test_resend_verification_user_not_found(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
) -> None:
    user_repository.get_user_by_email.return_value = None

    with pytest.raises(UserNotFoundError):
        verification_service.resend_verification("missing@example.com")


def test_resend_verification_already_verified(
    verification_service: EmailVerificationService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user(is_verified=True)
    user_repository.get_user_by_email.return_value = user

    with pytest.raises(EmailAlreadyVerifiedError):
        verification_service.resend_verification("user@example.com")

    token_repository.invalidate_unused_tokens.assert_not_called()
    token_repository.create_token.assert_not_called()
