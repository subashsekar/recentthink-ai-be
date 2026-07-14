"""Unit tests for FEATURE_MAX_TOKENS resolution."""

from __future__ import annotations

from app.core.feature_tokens import FEATURE_MAX_TOKENS, resolve_feature_max_tokens


def test_feature_limits_match_sprint_budget() -> None:
    assert FEATURE_MAX_TOKENS["leetcode"] == 1800
    assert FEATURE_MAX_TOKENS["hackerrank"] == 1800
    assert FEATURE_MAX_TOKENS["dsa_pattern"] == 3000
    assert FEATURE_MAX_TOKENS["course_generator"] == 4500
    assert FEATURE_MAX_TOKENS["interview"] == 2200


def test_resolve_uses_feature_table_when_no_override() -> None:
    assert resolve_feature_max_tokens("leetcode") == 1800
    assert resolve_feature_max_tokens("course_generator") == 4500
    assert resolve_feature_max_tokens("unknown_feature") == 1800


def test_explicit_override_wins() -> None:
    assert resolve_feature_max_tokens("leetcode", override=900) == 900


def test_requested_sections_scale_budget_down() -> None:
    full = resolve_feature_max_tokens("course_generator")
    partial = resolve_feature_max_tokens(
        "course_generator",
        requested_sections=["quiz", "project"],
    )
    assert partial < full
    assert partial >= 400


def test_limits_map_override() -> None:
    assert resolve_feature_max_tokens("leetcode", limits={"leetcode": 1200}) == 1200
