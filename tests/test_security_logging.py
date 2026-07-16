"""Tests for security event logging redaction."""

from __future__ import annotations

import logging

import pytest

from shared.logging.security import log_security_event


def test_log_security_event_strips_sensitive_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="security"):
        log_security_event(
            "login_failure",
            email="user@example.com",
            password="secret",
            refresh_token="token-value",
            endpoint="/auth/login",
        )

    assert "password=" not in caplog.text
    assert "refresh_token=" not in caplog.text
    assert "event=login_failure" in caplog.text
    assert "email=user@example.com" in caplog.text
    assert "endpoint=/auth/login" in caplog.text
