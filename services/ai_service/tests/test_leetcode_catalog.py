"""LeetCode catalog unit tests."""

from __future__ import annotations

import pytest

from app.agents.leetcode.catalog import (
    list_examples,
    list_modes,
    resolve_mode_id,
    validate_mode_id,
)
from shared.exceptions.base import ValidationException


def test_list_modes_returns_coaching_modes() -> None:
    modes = list_modes()
    assert len(modes) >= 4
    assert modes[0].id == "learning"
    assert modes[0].label
    assert modes[0].description is not None or modes[0].recommended in {True, False}


def test_list_examples_returns_starter_problems() -> None:
    examples = list_examples()
    assert len(examples) >= 3
    assert examples[0].url.startswith("https://leetcode.com/problems/")


def test_resolve_mode_id_defaults_to_learning() -> None:
    assert resolve_mode_id() == "learning"


def test_resolve_mode_id_uses_request_then_session() -> None:
    assert resolve_mode_id(requested="quick") == "quick"
    assert resolve_mode_id(session_mode_id="interview") == "interview"
    assert resolve_mode_id(requested="teacher", session_mode_id="quick") == "teacher"


def test_validate_mode_id_rejects_unknown() -> None:
    with pytest.raises(ValidationException):
        validate_mode_id("not-a-mode")


def test_resolve_mode_id_falls_back_to_learning_when_missing() -> None:
    assert resolve_mode_id(session_mode_id="learning") == "learning"
