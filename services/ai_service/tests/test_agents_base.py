"""Unit tests for JSON extraction utilities."""

from __future__ import annotations

import pytest

from app.agents.shared.base import extract_json_object


def test_extract_json_from_plain_object() -> None:
    result = extract_json_object('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_from_markdown_fence() -> None:
    text = '```json\n{"difficulty": "Easy"}\n```'
    result = extract_json_object(text)
    assert result["difficulty"] == "Easy"


def test_extract_json_invalid_raises() -> None:
    with pytest.raises(Exception):
        extract_json_object("not json")
