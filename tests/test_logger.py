"""Tests for structured logging helpers."""

from __future__ import annotations

import json
import logging

import pytest

from shared.config import Environment
from shared.logging.logger import StructuredFormatter, _use_json_logs, get_logger


def test_structured_formatter_emits_json() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    payload = json.loads(StructuredFormatter().format(record))
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"


def test_use_json_logs_honors_explicit_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_FORMAT", "json")
    assert _use_json_logs(object()) is True
    monkeypatch.setenv("LOG_FORMAT", "plain")
    assert _use_json_logs(object()) is False


def test_use_json_logs_defaults_to_json_in_production() -> None:
    class _Settings:
        environment = Environment.PRODUCTION

    assert _use_json_logs(_Settings()) is True


def test_get_logger_configures_root_handler_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    monkeypatch.delenv("LOG_FORMAT", raising=False)
    from shared.config import get_settings

    get_settings.cache_clear()
    try:
        first = get_logger("logger-test-a")
        second = get_logger("logger-test-b")
        assert first is not second
        assert root.handlers
    finally:
        get_settings.cache_clear()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
