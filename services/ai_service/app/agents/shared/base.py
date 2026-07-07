"""Shared utilities for LLM response parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class AgentResult:
    """Result of a single LLM invocation (legacy compatibility)."""

    content: str
    structured: BaseModel | None
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


def extract_json_object(text: str) -> dict:
    """Parse JSON from an LLM response, tolerating markdown fences."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)
