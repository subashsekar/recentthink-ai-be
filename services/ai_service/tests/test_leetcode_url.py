"""Unit tests for LeetCode URL utilities."""

from __future__ import annotations

import pytest

from app.utils.leetcode_url import (
    InvalidLeetCodeURLError,
    extract_leetcode_slug,
    is_valid_leetcode_url,
    normalize_leetcode_url,
)


def test_extract_slug_from_canonical_url() -> None:
    assert extract_leetcode_slug("https://leetcode.com/problems/two-sum/") == "two-sum"


def test_extract_slug_without_trailing_slash() -> None:
    assert extract_leetcode_slug("https://leetcode.com/problems/two-sum") == "two-sum"


def test_invalid_url_raises() -> None:
    with pytest.raises(InvalidLeetCodeURLError):
        extract_leetcode_slug("https://example.com/problems/two-sum/")


def test_is_valid_leetcode_url() -> None:
    assert is_valid_leetcode_url("https://leetcode.com/problems/two-sum/")
    assert not is_valid_leetcode_url("https://google.com")


def test_normalize_leetcode_url() -> None:
    assert (
        normalize_leetcode_url("two-sum")
        == "https://leetcode.com/problems/two-sum/"
    )
