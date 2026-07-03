"""Tests for Sentry integration and event filtering."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from shared.exceptions.auth import ForbiddenError, InvalidCredentialsError
from shared.exceptions.base import ValidationException
from shared.monitoring.sentry import before_send, init_sentry


def test_before_send_filters_auth_exceptions() -> None:
    event: dict = {"message": "test"}
    hint = {"exc_info": (ForbiddenError, ForbiddenError("denied"), None)}
    assert before_send(event, hint) is None


def test_before_send_filters_validation_exceptions() -> None:
    event: dict = {"message": "test"}
    hint = {
        "exc_info": (
            ValidationException,
            ValidationException("bad input"),
            None,
        ),
    }
    assert before_send(event, hint) is None


def test_before_send_filters_invalid_credentials() -> None:
    event: dict = {"message": "test"}
    hint = {
        "exc_info": (
            InvalidCredentialsError,
            InvalidCredentialsError("bad creds"),
            None,
        ),
    }
    assert before_send(event, hint) is None


def test_before_send_filters_401_status_codes() -> None:
    event: dict = {"contexts": {"response": {"status_code": 401}}}
    assert before_send(event, {}) is None


def test_before_send_filters_403_status_codes() -> None:
    event: dict = {"tags": {"http.status_code": 403}}
    assert before_send(event, {}) is None


def test_before_send_scrubs_sensitive_extra_fields() -> None:
    event: dict = {
        "extra": {
            "user_id": "abc",
            "password": "secret",
            "refresh_token": "token-value",
        },
    }
    result = before_send(event, {})
    assert result is not None
    assert result["extra"]["password"] == "[Filtered]"
    assert result["extra"]["refresh_token"] == "[Filtered]"
    assert result["extra"]["user_id"] == "abc"


def test_before_send_passes_unhandled_exceptions() -> None:
    event: dict = {"message": "unexpected failure"}
    hint = {"exc_info": (RuntimeError, RuntimeError("boom"), None)}
    result = before_send(event, hint)
    assert result is not None
    assert result["message"] == "unexpected failure"


def test_init_sentry_skips_when_dsn_unset() -> None:
    mock_settings = MagicMock()
    mock_settings.sentry_dsn = None
    init_sentry(mock_settings)


def test_init_sentry_initialises_when_dsn_set() -> None:
    mock_settings = MagicMock()
    mock_settings.sentry_dsn = "https://example@sentry.io/1"
    mock_settings.sentry_environment = "test"
    mock_settings.environment.value = "test"
    mock_settings.sentry_release = "1.0.0"
    mock_settings.sentry_traces_sample_rate = 0.1

    mock_sentry = MagicMock()
    mock_fastapi_integration = MagicMock()
    mock_logging_integration = MagicMock()
    mock_sqlalchemy_integration = MagicMock()

    with patch.dict(
        "sys.modules",
        {
            "sentry_sdk": mock_sentry,
            "sentry_sdk.integrations.fastapi": MagicMock(
                FastApiIntegration=mock_fastapi_integration,
            ),
            "sentry_sdk.integrations.logging": MagicMock(
                LoggingIntegration=mock_logging_integration,
            ),
            "sentry_sdk.integrations.sqlalchemy": MagicMock(
                SqlalchemyIntegration=mock_sqlalchemy_integration,
            ),
        },
    ):
        init_sentry(mock_settings)
        mock_sentry.init.assert_called_once()
