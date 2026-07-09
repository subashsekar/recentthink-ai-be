"""Tests for first-class coaching mode registry."""

from __future__ import annotations

from app.coaching.registry import DEFAULT_MODE_ID, get_mode_registry


def test_mode_registry_lists_modes() -> None:
    modes = get_mode_registry().list_metadata()
    assert len(modes) >= 4
    assert any(m.id == DEFAULT_MODE_ID for m in modes)


def test_mode_registry_resolves_unknown_to_learning() -> None:
    cfg = get_mode_registry().resolve("not-a-mode")
    assert cfg.metadata.id == DEFAULT_MODE_ID

