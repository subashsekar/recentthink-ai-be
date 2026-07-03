"""Unit tests for PasswordResetService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import ANY, MagicMock
from uuid import uuid4

import pytest

from app.security.tokens import hash_token
from app.services.email.base import EmailService
from app.services.password_reset_service import PasswordResetService
from shared.config import Settings
from shared.exceptions.auth import (
    ExpiredTokenError,
    InvalidTokenError,
    UsedTokenError,
    UserNotFoundError,
)
from shared.exceptions.email import EmailDeliveryError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        app_name="RecentThink",
        email_support_address="support@example.com",
        password_reset_url="https://app.example.com/reset-password",
        password_reset_token_expire_hours=1,
    )


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def token_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def refresh_token_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def password_service() -> MagicMock:
    service = MagicMock()
    service.hash.return_value = "new-hash"
    return service


@pytest.fixture
def email_service() -> MagicMock:
    return MagicMock(spec=EmailService)


@pytest.fixture
def db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def reset_service(
    db: MagicMock,
    user_repository: MagicMock,
    token_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
    email_service: MagicMock,
    settings: Settings,
) -> PasswordResetService:
    token_repository.consume_token.return_value = True
    return PasswordResetService(
        db=db,
        user_repository=user_repository,
        password_reset_repository=token_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        email_service=email_service,
        settings=settings,
    )


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.first_name = "Jane"
    user.email = "user@example.com"
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


def test_request_password_reset_existing_email(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user = _make_user()
    user_repository.get_user_by_email.return_value = user

    reset_service.request_password_reset("user@example.com")

    token_repository.invalidate_unused_tokens.assert_called_once_with(user.id)
    token_repository.create_token.assert_called_once()
    email_service.send_email.assert_called_once()


def test_request_password_reset_unknown_email(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user_repository.get_user_by_email.return_value = None

    reset_service.request_password_reset("missing@example.com")

    token_repository.invalidate_unused_tokens.assert_not_called()
    token_repository.create_token.assert_not_called()
    email_service.send_email.assert_not_called()


def test_request_password_reset_stores_hashed_token(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    token_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user_repository.get_user_by_email.return_value = _make_user()

    reset_service.request_password_reset("user@example.com")

    stored_token = token_repository.create_token.call_args.kwargs["token"]
    assert len(stored_token) == 64
    message = email_service.send_email.call_args.args[0]
    raw_token = message.html_body.split("token=")[1].split('"')[0].split("&")[0]
    assert hash_token(raw_token) == stored_token


def test_request_password_reset_invalidates_previous_tokens(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    user = _make_user()
    user_repository.get_user_by_email.return_value = user

    reset_service.request_password_reset("user@example.com")

    token_repository.invalidate_unused_tokens.assert_called_once_with(user.id)


def test_request_password_reset_email_failure_does_not_raise(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    email_service: MagicMock,
) -> None:
    user_repository.get_user_by_email.return_value = _make_user()
    email_service.send_email.side_effect = EmailDeliveryError("smtp down")

    reset_service.request_password_reset("user@example.com")


def test_reset_password_success(
    reset_service: PasswordResetService,
    db: MagicMock,
    user_repository: MagicMock,
    token_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
) -> None:
    user = _make_user()
    stored = _make_token(user_id=user.id)
    token_repository.get_by_token.return_value = stored
    user_repository.get_user_by_id.return_value = user

    reset_service.reset_password("raw-token", "NewSecure1!")

    password_service.hash.assert_called_once_with("NewSecure1!")
    token_repository.consume_token.assert_called_once_with(stored.id, commit=False)
    user_repository.update_user.assert_called_once_with(
        user.id,
        commit=False,
        password_hash="new-hash",
        password_changed_at=ANY,
    )
    refresh_token_repository.revoke_all_tokens.assert_called_once_with(
        user.id,
        commit=False,
    )
    db.commit.assert_called_once()


def test_reset_password_lost_race_raises_used(
    reset_service: PasswordResetService,
    db: MagicMock,
    user_repository: MagicMock,
    token_repository: MagicMock,
    refresh_token_repository: MagicMock,
) -> None:
    user = _make_user()
    token_repository.get_by_token.return_value = _make_token(user_id=user.id)
    user_repository.get_user_by_id.return_value = user
    # A concurrent reset already consumed the token.
    token_repository.consume_token.return_value = False

    with pytest.raises(UsedTokenError):
        reset_service.reset_password("raw-token", "NewSecure1!")

    user_repository.update_user.assert_not_called()
    refresh_token_repository.revoke_all_tokens.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


def test_reset_password_invalid_token(
    reset_service: PasswordResetService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = None

    with pytest.raises(InvalidTokenError):
        reset_service.reset_password("missing", "NewSecure1!")


def test_reset_password_used_token(
    reset_service: PasswordResetService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(
        user_id=uuid4(),
        is_used=True,
    )

    with pytest.raises(UsedTokenError):
        reset_service.reset_password("used", "NewSecure1!")


def test_reset_password_expired_token(
    reset_service: PasswordResetService,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(
        user_id=uuid4(),
        expires_at=datetime.now(tz=UTC) - timedelta(hours=1),
    )

    with pytest.raises(ExpiredTokenError):
        reset_service.reset_password("expired", "NewSecure1!")


def test_reset_password_user_not_found(
    reset_service: PasswordResetService,
    user_repository: MagicMock,
    token_repository: MagicMock,
) -> None:
    token_repository.get_by_token.return_value = _make_token(user_id=uuid4())
    user_repository.get_user_by_id.return_value = None

    with pytest.raises(UserNotFoundError):
        reset_service.reset_password("raw-token", "NewSecure1!")
