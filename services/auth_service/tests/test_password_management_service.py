"""Unit tests for PasswordManagementService."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock
from uuid import uuid4

import pytest

from app.security.tokens import hash_token
from app.services.password_management_service import PasswordManagementService
from shared.config import Settings
from shared.exceptions.auth import InvalidCredentialsError, PasswordReuseError


@pytest.fixture
def settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        change_password_keep_current_session=False,
    )


@pytest.fixture
def user_repository() -> MagicMock:
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
def db() -> MagicMock:
    return MagicMock()


@pytest.fixture
def management_service(
    db: MagicMock,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
    settings: Settings,
) -> PasswordManagementService:
    return PasswordManagementService(
        db=db,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        settings=settings,
    )


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.password_hash = "old-hash"
    return user


def test_change_password_success(
    management_service: PasswordManagementService,
    db: MagicMock,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
) -> None:
    user = _make_user()
    password_service.verify.side_effect = lambda plain, hashed: plain == "Current1!"

    management_service.change_password(
        user,
        current_password="Current1!",
        new_password="NewSecure1!",
    )

    password_service.hash.assert_called_once_with("NewSecure1!")
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


def test_change_password_invalid_current_password(
    management_service: PasswordManagementService,
    password_service: MagicMock,
) -> None:
    user = _make_user()
    password_service.verify.return_value = False

    with pytest.raises(InvalidCredentialsError):
        management_service.change_password(
            user,
            current_password="Wrong1!",
            new_password="NewSecure1!",
        )


def test_change_password_rejects_reuse(
    management_service: PasswordManagementService,
    password_service: MagicMock,
) -> None:
    user = _make_user()
    password_service.verify.side_effect = lambda plain, hashed: True

    with pytest.raises(PasswordReuseError):
        management_service.change_password(
            user,
            current_password="SamePass1!",
            new_password="SamePass1!",
        )


def test_change_password_revokes_all_tokens_by_default(
    management_service: PasswordManagementService,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
) -> None:
    user = _make_user()
    password_service.verify.side_effect = lambda plain, hashed: plain == "Current1!"

    management_service.change_password(
        user,
        current_password="Current1!",
        new_password="NewSecure1!",
        refresh_token="session-token",
    )

    refresh_token_repository.revoke_all_tokens.assert_called_once_with(
        user.id,
        commit=False,
    )
    refresh_token_repository.revoke_all_tokens_except.assert_not_called()


def test_change_password_keeps_current_session_when_configured(
    db: MagicMock,
    user_repository: MagicMock,
    refresh_token_repository: MagicMock,
    password_service: MagicMock,
) -> None:
    settings = Settings(
        secret_key="x" * 32,
        change_password_keep_current_session=True,
    )
    service = PasswordManagementService(
        db=db,
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
        password_service=password_service,
        settings=settings,
    )
    user = _make_user()
    password_service.verify.side_effect = lambda plain, hashed: plain == "Current1!"
    keep_hash = hash_token("session-token")
    stored = MagicMock()
    stored.user_id = user.id
    stored.is_revoked = False
    refresh_token_repository.get_by_token_hash.return_value = stored

    service.change_password(
        user,
        current_password="Current1!",
        new_password="NewSecure1!",
        refresh_token="session-token",
    )

    refresh_token_repository.revoke_all_tokens_except.assert_called_once_with(
        user.id,
        keep_token_hash=keep_hash,
        commit=False,
    )
    refresh_token_repository.revoke_all_tokens.assert_not_called()
