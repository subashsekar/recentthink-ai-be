"""LeetCode coaching mode catalog and prompt helpers."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.agents.leetcode.schemas import LeetCodeExampleResponse, LeetCodeModeResponse
from app.agents.shared.coaching_modes import DEFAULT_MODE_ID, build_mode_prompt_prefix, get_mode_instructions
from shared.exceptions.base import ValidationException

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "config" / "leetcode_catalog.json"


@lru_cache(maxsize=1)
def _load_catalog() -> dict:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def _mode_entries() -> list[dict]:
    return [item for item in _load_catalog().get("modes", []) if isinstance(item, dict)]


def allowed_mode_ids() -> list[str]:
    return [str(item["id"]) for item in _mode_entries() if item.get("id")]


def list_modes() -> list[LeetCodeModeResponse]:
    """Return coaching modes for the workspace header."""
    return [
        LeetCodeModeResponse(id=str(item["id"]), label=str(item["label"]))
        for item in _mode_entries()
        if item.get("id") and item.get("label")
    ]


def list_examples() -> list[LeetCodeExampleResponse]:
    """Return starter example problems for the hero section."""
    return [
        LeetCodeExampleResponse.model_validate(item)
        for item in _load_catalog().get("examples", [])
        if isinstance(item, dict)
    ]


def validate_mode_id(mode_id: str) -> None:
    """Reject unknown coaching mode IDs."""
    if mode_id not in allowed_mode_ids():
        raise ValidationException(
            f"Unknown mode_id '{mode_id}'. Use GET /leetcode/modes for valid ids.",
        )


def resolve_mode_id(
    *,
    requested: str | None = None,
    session_mode_id: str | None = None,
) -> str:
    """Pick mode: explicit request → session → default learning."""
    if requested is not None:
        validate_mode_id(requested)
        return requested
    if isinstance(session_mode_id, str) and session_mode_id:
        validate_mode_id(session_mode_id)
        return session_mode_id
    return DEFAULT_MODE_ID


__all__ = [
    "DEFAULT_MODE_ID",
    "allowed_mode_ids",
    "build_mode_prompt_prefix",
    "get_mode_instructions",
    "list_examples",
    "list_modes",
    "resolve_mode_id",
    "validate_mode_id",
]

