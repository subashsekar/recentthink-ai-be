"""OpenRouter streaming chunk parsing helpers."""

from __future__ import annotations

import json
from typing import Any


def parse_stream_delta(chunk: str) -> str:
    """Extract text delta from an OpenRouter SSE data chunk."""
    if not chunk or chunk == "[DONE]":
        return ""
    try:
        payload = json.loads(chunk)
    except json.JSONDecodeError:
        return ""
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    delta = choices[0].get("delta") if isinstance(choices[0], dict) else None
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    return content if isinstance(content, str) else ""


def parse_stream_metadata(chunk: str) -> dict[str, Any]:
    """Extract model/provider/usage/finish_reason metadata from a stream chunk."""
    if not chunk or chunk == "[DONE]":
        return {}
    try:
        payload = json.loads(chunk)
    except json.JSONDecodeError:
        return {}
    result: dict[str, Any] = {}
    if isinstance(payload.get("model"), str):
        result["model"] = payload["model"]
    usage = payload.get("usage")
    if isinstance(usage, dict):
        result["usage"] = usage
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        choice = choices[0]
        if isinstance(choice, dict):
            finish_reason = choice.get("finish_reason")
            if isinstance(finish_reason, str) and finish_reason:
                result["finish_reason"] = finish_reason
    return result
