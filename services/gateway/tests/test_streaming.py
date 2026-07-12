"""Unit tests for gateway streaming helpers and proxy utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.proxy.streaming import should_stream


def test_should_stream_accept_event_stream() -> None:
    request = MagicMock()
    request.headers = {"accept": "text/event-stream"}
    request.query_params = {}
    assert should_stream(request) is True


def test_should_stream_query_true() -> None:
    request = MagicMock()
    request.headers = {}
    request.query_params = {"stream": "true"}
    assert should_stream(request) is True


@pytest.mark.parametrize("value", ["1", "yes", "TRUE"])
def test_should_stream_query_truthy(value: str) -> None:
    request = MagicMock()
    request.headers = {}
    request.query_params = {"stream": value}
    assert should_stream(request) is True


def test_should_stream_false_by_default() -> None:
    request = MagicMock()
    request.headers = {"accept": "application/json"}
    request.query_params = {}
    assert should_stream(request) is False
