"""Tests for structured security logging."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from datetime import UTC, datetime

from shared.logging.security import log_security_event


def test_log_security_event_emits_structured_message(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="security"):
        log_security_event("login_success", user_id="abc-123", email="user@example.com")

    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert "event=login_success" in message
    assert "user_id=abc-123" in message
    assert "email=user@example.com" in message


def test_log_security_event_strips_sensitive_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="security"):
        log_security_event(
            "login_failure",
            email="user@example.com",
            password="SecretPass1!",
            refresh_token="should-not-appear",
        )

    message = caplog.records[0].message
    assert "password" not in message
    assert "refresh_token" not in message
    assert "SecretPass1" not in message
    assert "should-not-appear" not in message
    assert "email=user@example.com" in message


def test_auth_service_logs_registration_on_success() -> None:
    from app.services.auth_service import AuthService

    mock_users = MagicMock()
    mock_refresh = MagicMock()
    mock_passwords = MagicMock()
    mock_jwt = MagicMock()
    mock_email_verification = MagicMock()

    from app.models.enums import Role

    user = MagicMock()
    user.id = uuid4()
    user.first_name = "New"
    user.last_name = "User"
    user.email = "new@example.com"
    user.role = Role.USER
    user.is_verified = False
    user.is_active = True
    user.created_at = datetime.now(tz=UTC)
    user.updated_at = datetime.now(tz=UTC)
    mock_users.create_user.return_value = user
    mock_passwords.hash.return_value = "hash"

    service = AuthService(
        user_repository=mock_users,
        refresh_token_repository=mock_refresh,
        password_service=mock_passwords,
        jwt_service=mock_jwt,
        email_verification_service=mock_email_verification,
    )

    from app.schemas.auth import RegisterRequest

    with patch("app.services.auth_service.log_security_event") as mock_log:
        service.register(
            RegisterRequest(
                first_name="New",
                last_name="User",
                email="new@example.com",
                password="SecurePass1!",
            ),
        )
        mock_log.assert_called_once_with(
            "registration",
            user_id=str(user.id),
            email=user.email,
        )


def test_auth_service_logs_login_failure() -> None:
    from app.services.auth_service import AuthService

    mock_users = MagicMock()
    mock_users.get_user_by_email.return_value = None

    service = AuthService(
        user_repository=mock_users,
        refresh_token_repository=MagicMock(),
        password_service=MagicMock(),
        jwt_service=MagicMock(),
        email_verification_service=MagicMock(),
    )

    from app.schemas.auth import LoginRequest
    from shared.exceptions.auth import InvalidCredentialsError

    with patch("app.services.auth_service.log_security_event") as mock_log:
        with pytest.raises(InvalidCredentialsError):
            service.login(LoginRequest(email="fail@example.com", password="wrong"))
        mock_log.assert_called_once_with("login_failure", email="fail@example.com")
