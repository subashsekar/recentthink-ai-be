"""Prompt injection sanitization utilities."""

from __future__ import annotations

import re

_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)disregard\s+(all\s+)?(previous|prior)\s+instructions"),
    re.compile(r"(?i)you\s+are\s+now\s+"),
    re.compile(r"(?i)system\s*:\s*"),
    re.compile(r"(?i)```\s*system"),
    re.compile(r"(?i)<\s*/?\s*system\s*>"),
)

_MAX_SANITIZED_LENGTH = 32000


def sanitize_user_input(text: str, *, max_length: int = _MAX_SANITIZED_LENGTH) -> str:
    """Strip common prompt-injection patterns and enforce length limits."""
    cleaned = text.strip()
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[filtered]", cleaned)
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned
