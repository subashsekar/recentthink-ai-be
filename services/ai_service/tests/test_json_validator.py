"""JSON validation layer tests."""

from __future__ import annotations

import pytest

from app.schemas.llm_response import UnifiedLLMResponse
from app.services.json_validator import JSONValidationError, JSONValidator


def test_validate_success() -> None:
    validator = JSONValidator()
    content = (
        '{"teacher":{"thinking_process":"step","concepts":[],"approach":"hash"},'
        '"coder":{"language":"python","solutions":[]},'
        '"evaluator":{"time_complexity":"O(n)","space_complexity":"O(1)"}}'
    )
    result = validator.validate(content, UnifiedLLMResponse)
    assert result.success is True
    assert result.data is not None


def test_validate_invalid_json() -> None:
    validator = JSONValidator()
    result = validator.validate("not json", UnifiedLLMResponse)
    assert result.success is False
    assert result.error is not None


def test_validate_or_raise() -> None:
    validator = JSONValidator()
    with pytest.raises(JSONValidationError):
        validator.validate_or_raise("{bad", UnifiedLLMResponse)


def test_validate_tolerates_markdown_fence() -> None:
    validator = JSONValidator()
    content = '```json\n{"teacher":{},"coder":{},"evaluator":{}}\n```'
    result = validator.validate(content, UnifiedLLMResponse)
    assert result.success is True
