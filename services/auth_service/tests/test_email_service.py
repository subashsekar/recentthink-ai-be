"""Unit tests for the email delivery subsystem."""

from __future__ import annotations

import smtplib
from unittest.mock import patch

import pytest

from app.services.email.base import EmailMessage
from app.services.email.console_sender import ConsoleEmailService
from app.services.email.factory import build_email_service
from app.services.email.smtp_sender import SMTPEmailService
from app.services.email.templates import build_password_reset_email, build_verification_email
from shared.config import EmailProvider, Settings
from shared.exceptions.email import EmailDeliveryError


def _message() -> EmailMessage:
    return EmailMessage(
        to_email="user@example.com",
        subject="Verify your email",
        html_body="<p>Hello</p>",
        text_body="Hello",
    )


def test_console_sender_does_not_raise() -> None:
    sender = ConsoleEmailService(from_address="no-reply@x.com", from_name="X")
    sender.send_email(_message())


def test_smtp_sender_sends_message() -> None:
    sender = SMTPEmailService(
        host="smtp.example.com",
        port=587,
        from_address="no-reply@x.com",
        from_name="X",
        username="user",
        password="secret",
        use_tls=True,
    )

    with patch("app.services.email.smtp_sender.smtplib.SMTP") as smtp_cls:
        server = smtp_cls.return_value.__enter__.return_value
        sender.send_email(_message())

    server.starttls.assert_called_once()
    server.login.assert_called_once_with("user", "secret")
    server.send_message.assert_called_once()


def test_smtp_sender_wraps_failure() -> None:
    sender = SMTPEmailService(
        host="smtp.example.com",
        port=587,
        from_address="no-reply@x.com",
        from_name="X",
    )

    with patch("app.services.email.smtp_sender.smtplib.SMTP") as smtp_cls:
        smtp_cls.return_value.__enter__.return_value.send_message.side_effect = (
            smtplib.SMTPException("boom")
        )
        with pytest.raises(EmailDeliveryError):
            sender.send_email(_message())


def test_smtp_sender_skips_login_without_credentials() -> None:
    sender = SMTPEmailService(
        host="smtp.example.com",
        port=25,
        from_address="no-reply@x.com",
        from_name="X",
        use_tls=False,
    )

    with patch("app.services.email.smtp_sender.smtplib.SMTP") as smtp_cls:
        server = smtp_cls.return_value.__enter__.return_value
        sender.send_email(_message())

    server.starttls.assert_not_called()
    server.login.assert_not_called()
    server.send_message.assert_called_once()


def test_factory_returns_console_by_default() -> None:
    settings = Settings(secret_key="x" * 32, email_provider=EmailProvider.CONSOLE)
    assert isinstance(build_email_service(settings), ConsoleEmailService)


def test_factory_returns_smtp_when_configured() -> None:
    settings = Settings(
        secret_key="x" * 32,
        email_provider=EmailProvider.SMTP,
        smtp_host="smtp.example.com",
    )
    assert isinstance(build_email_service(settings), SMTPEmailService)


def test_verification_template_contains_link_and_support() -> None:
    message = build_verification_email(
        to_email="user@example.com",
        recipient_name="Jane",
        verification_link="https://app.example.com/verify?token=abc123",
        expire_hours=24,
        app_name="RecentThink",
        support_email="support@example.com",
    )

    assert message.to_email == "user@example.com"
    assert "https://app.example.com/verify?token=abc123" in message.html_body
    assert "24 hour" in message.html_body
    assert "support@example.com" in message.html_body
    assert "Verify Email" in message.html_body
    # Plain-text fallback is always provided.
    assert message.text_body is not None
    assert "https://app.example.com/verify?token=abc123" in message.text_body


def test_verification_template_escapes_recipient_name() -> None:
    message = build_verification_email(
        to_email="user@example.com",
        recipient_name="<script>alert(1)</script>",
        verification_link="https://app.example.com/verify?token=abc",
        expire_hours=24,
        app_name="RecentThink",
        support_email="support@example.com",
    )

    assert "<script>" not in message.html_body
    assert "&lt;script&gt;" in message.html_body


def test_password_reset_template_contains_link_and_security_notice() -> None:
    message = build_password_reset_email(
        to_email="user@example.com",
        recipient_name="Jane",
        reset_link="https://app.example.com/reset-password?token=abc123",
        expire_hours=1,
        app_name="RecentThink",
        support_email="support@example.com",
    )

    assert message.to_email == "user@example.com"
    assert "https://app.example.com/reset-password?token=abc123" in message.html_body
    assert "Reset Password" in message.html_body
    assert "1 hour" in message.html_body
    assert "Security notice" in message.html_body
    assert "support@example.com" in message.text_body
