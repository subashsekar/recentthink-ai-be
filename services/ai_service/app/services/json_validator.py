"""JSON validation layer for LLM structured responses."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.agents.shared.base import extract_json_object
from shared.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of JSON validation."""

    success: bool
    data: BaseModel | None
    raw: dict | None
    error: str | None = None


class JSONValidationError(Exception):
    """Raised when JSON validation fails after retries."""

    def __init__(self, message: str, *, raw_content: str | None = None) -> None:
        super().__init__(message)
        self.raw_content = raw_content


class JSONValidator:
    """Validate LLM responses against Pydantic schemas with tolerant parsing."""

    def validate(
        self,
        content: str,
        schema: type[T],
        *,
        max_parse_attempts: int = 2,
    ) -> ValidationResult:
        last_error: str | None = None
        for attempt in range(max_parse_attempts):
            try:
                payload = extract_json_object(content)
                validated = schema.model_validate(payload)
                return ValidationResult(success=True, data=validated, raw=payload)
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)
                logger.warning(
                    "json_validation_failed",
                    extra={"attempt": attempt + 1, "error": last_error},
                )
        return ValidationResult(
            success=False,
            data=None,
            raw=None,
            error=last_error or "Unknown validation error",
        )

    def validate_or_raise(self, content: str, schema: type[T]) -> T:
        result = self.validate(content, schema)
        if not result.success or result.data is None:
            raise JSONValidationError(
                result.error or "Validation failed",
                raw_content=content[:500],
            )
        return result.data  # type: ignore[return-value]
