"""Auth account block / disable separation tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.models.enums import Role
from app.schemas.account import EnableAccountRequest
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.schemas.auth import LoginRequest

from shared.exceptions.auth import BlockedUserError, InactiveUserError


def _user(**overrides):
    user = MagicMock()
    user.id = overrides.get("id", uuid4())
    user.email = overrides.get("email", "u@example.com")
    user.password_hash = "hash"
    user.role = overrides.get("role", Role.USER)
    user.is_active = overrides.get("is_active", True)
    user.is_blocked = overrides.get("is_blocked", False)
    user.is_verified = True
    user.password_changed_at = datetime.now(tz=UTC)
    user.disabled_at = None
    user.blocked_at = None
    user.first_name = "A"
    user.last_name = "B"
    user.created_at = datetime.now(tz=UTC)
    user.updated_at = datetime.now(tz=UTC)
    return user


def test_login_rejects_blocked_user() -> None:
    users = MagicMock()
    user = _user(is_blocked=True)
    users.get_user_by_email.return_value = user
    passwords = MagicMock()
    passwords.verify.return_value = True
    service = AuthService(
        user_repository=users,
        refresh_token_repository=MagicMock(),
        password_service=passwords,
        jwt_service=MagicMock(),
        email_verification_service=MagicMock(),
    )
    with pytest.raises(BlockedUserError):
        service.login(LoginRequest(email="u@example.com", password="x"))


def test_login_rejects_inactive_user() -> None:
    users = MagicMock()
    user = _user(is_active=False)
    users.get_user_by_email.return_value = user
    passwords = MagicMock()
    passwords.verify.return_value = True
    service = AuthService(
        user_repository=users,
        refresh_token_repository=MagicMock(),
        password_service=passwords,
        jwt_service=MagicMock(),
        email_verification_service=MagicMock(),
    )
    with pytest.raises(InactiveUserError):
        service.login(LoginRequest(email="u@example.com", password="x"))


def test_enable_rejected_when_blocked() -> None:
    users = MagicMock()
    user = _user(is_active=False, is_blocked=True)
    users.get_user_by_email.return_value = user
    passwords = MagicMock()
    passwords.verify.return_value = True
    service = AccountService(
        db=MagicMock(),
        user_repository=users,
        refresh_token_repository=MagicMock(),
        email_verification_repository=MagicMock(),
        password_reset_repository=MagicMock(),
        password_service=passwords,
    )
    with pytest.raises(BlockedUserError):
        service.enable_account(
            EnableAccountRequest(email="u@example.com", password="secret")
        )
