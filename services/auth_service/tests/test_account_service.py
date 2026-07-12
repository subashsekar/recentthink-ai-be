"""Unit tests for AccountService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from shared.exceptions.auth import InvalidCredentialsError
from shared.exceptions.base import BusinessException


def _make_user(*, is_active: bool = True, password: str = "ValidP@ss1") -> MagicMock:
    from app.services.password_service import PasswordService

    user = MagicMock()
    user.id = uuid4()
    user.email = "jane@example.com"
    user.password_hash = PasswordService().hash(password)
    user.is_active = is_active
    user.is_blocked = False
    user.disabled_at = None if is_active else datetime.now(tz=UTC)
    user.blocked_at = None
    return user


def _service(user_repo=None, refresh=None, email=None, reset=None):
    from app.services.account_service import AccountService
    from app.services.password_service import PasswordService

    return AccountService(
        db=MagicMock(),
        user_repository=user_repo or MagicMock(),
        refresh_token_repository=refresh or MagicMock(),
        email_verification_repository=email or MagicMock(),
        password_reset_repository=reset or MagicMock(),
        password_service=PasswordService(),
    )


def test_disable_account_success() -> None:
    from app.schemas.account import DisableAccountRequest

    user = _make_user()
    users = MagicMock()
    refresh = MagicMock()
    updated = _make_user(is_active=False)
    updated.disabled_at = datetime.now(tz=UTC)
    users.update_user.return_value = updated
    service = _service(user_repo=users, refresh=refresh)

    with patch("app.services.account_service.log_security_event") as audit:
        result = service.disable_account(
            user,
            DisableAccountRequest(password="ValidP@ss1"),
            ip="127.0.0.1",
            user_agent="pytest",
        )

    assert result.is_active is False
    assert result.disabled_at is not None
    users.update_user.assert_called_once()
    refresh.revoke_all_tokens.assert_called_once_with(user.id, commit=False)
    assert audit.call_args.args[0] == "user_disabled_account"


def test_disable_wrong_password() -> None:
    from app.schemas.account import DisableAccountRequest

    service = _service()
    with pytest.raises(InvalidCredentialsError):
        service.disable_account(
            _make_user(),
            DisableAccountRequest(password="WrongPass1!"),
        )


def test_disable_already_disabled() -> None:
    from app.schemas.account import DisableAccountRequest

    service = _service()
    with pytest.raises(BusinessException, match="already disabled"):
        service.disable_account(
            _make_user(is_active=False),
            DisableAccountRequest(password="ValidP@ss1"),
        )


def test_delete_requires_confirm() -> None:
    from app.schemas.account import DeleteAccountRequest

    service = _service()
    with pytest.raises(BusinessException, match="confirm=true"):
        service.delete_account(
            _make_user(),
            DeleteAccountRequest(password="ValidP@ss1", confirm=False),
        )


def test_delete_success() -> None:
    from app.schemas.account import DeleteAccountRequest

    user = _make_user()
    users = MagicMock()
    refresh = MagicMock()
    email = MagicMock()
    reset = MagicMock()
    service = _service(user_repo=users, refresh=refresh, email=email, reset=reset)

    with patch("app.services.account_service.publish_account_deleted") as event:
        with patch("app.services.account_service.log_security_event") as audit:
            service.delete_account(
                user,
                DeleteAccountRequest(password="ValidP@ss1", confirm=True),
                ip="10.0.0.1",
                user_agent="pytest",
            )

    refresh.revoke_all_tokens.assert_called_once_with(user.id, commit=False)
    email.invalidate_unused_tokens.assert_called_once_with(user.id)
    reset.invalidate_unused_tokens.assert_called_once_with(user.id)
    users.delete_user.assert_called_once_with(user.id)
    event.assert_called_once()
    assert audit.call_args.args[0] == "user_deleted_account"


def test_delete_wrong_password() -> None:
    from app.schemas.account import DeleteAccountRequest

    service = _service()
    with pytest.raises(InvalidCredentialsError):
        service.delete_account(
            _make_user(),
            DeleteAccountRequest(password="WrongPass1!", confirm=True),
        )


def test_get_status() -> None:
    user = _make_user()
    status = _service().get_status(user)
    assert status.is_active is True
    assert status.disabled_at is None
