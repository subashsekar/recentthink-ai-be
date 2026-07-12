"""Unit tests for HackerRank URL parsing utilities."""

from __future__ import annotations

import pytest

from app.utils.hackerrank_url import InvalidHackerRankURLError, extract_hackerrank_slug, is_valid_hackerrank_url


@pytest.mark.parametrize(
    ("url", "slug"),
    [
        ("https://www.hackerrank.com/challenges/solve-me-first/problem", "solve-me-first"),
        ("https://hackerrank.com/challenges/two-strings/problem", "two-strings"),
        ("https://www.hackerrank.com/challenges/two-strings", "two-strings"),
        (
            "https://www.hackerrank.com/domains/algorithms/implementation/challenges/grading/problem",
            "grading",
        ),
    ],
)
def test_extract_hackerrank_slug(url: str, slug: str) -> None:
    assert extract_hackerrank_slug(url) == slug


def test_extract_hackerrank_slug_invalid() -> None:
    with pytest.raises(InvalidHackerRankURLError):
        extract_hackerrank_slug("https://example.com/not-hackerrank")


def test_is_valid_hackerrank_url() -> None:
    assert is_valid_hackerrank_url("https://www.hackerrank.com/challenges/solve-me-first/problem")
    assert not is_valid_hackerrank_url("https://www.hackerrank.com/")

