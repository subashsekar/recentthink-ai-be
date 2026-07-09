"""Coaching mode prompt helpers for shared workflow (no LeetCode package imports)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DEFAULT_MODE_ID = "learning"

_CATALOG_PATH = Path(__file__).resolve().parents[2] / "config" / "leetcode_catalog.json"


@lru_cache(maxsize=1)
def _load_modes() -> list[dict]:
    raw = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    return [item for item in raw.get("modes", []) if isinstance(item, dict)]


def get_mode_instructions(mode_id: str) -> str:
    """Return LLM system-prompt instructions for a coaching mode."""
    for item in _load_modes():
        if item.get("id") == mode_id:
            return str(item.get("instructions") or "")
    return ""


def get_mode_label(mode_id: str) -> str:
    for item in _load_modes():
        if item.get("id") == mode_id:
            return str(item.get("label") or mode_id)
    return mode_id


def build_mode_prompt_prefix(mode_id: str | None) -> str:
    """Prefix for system prompts so the LLM follows the selected coaching mode."""
    resolved = mode_id or DEFAULT_MODE_ID
    instructions = get_mode_instructions(resolved)
    if not instructions:
        return ""
    label = get_mode_label(resolved)
    return f"## Coaching mode: {label} ({resolved})\n{instructions}\n\n"
