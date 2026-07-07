"""LeetCode URL validation and slug extraction utilities."""

from __future__ import annotations

import re
from urllib.parse import urlparse

LEETCODE_PROBLEM_PATTERN = re.compile(
    r"^https?://(?:www\.)?leetcode\.com/problems/(?P<slug>[a-z0-9-]+)/?(?:\?.*)?$",
    re.IGNORECASE,
)


class InvalidLeetCodeURLError(ValueError):
    """Raised when a URL is not a valid LeetCode problem link."""


def extract_leetcode_slug(url: str) -> str:
    """Extract the problem slug from a LeetCode problem URL."""
    normalized = url.strip()
    match = LEETCODE_PROBLEM_PATTERN.match(normalized)
    if not match:
        raise InvalidLeetCodeURLError(
            "Invalid LeetCode URL. Expected format: "
            "https://leetcode.com/problems/two-sum/",
        )
    return match.group("slug")


def is_valid_leetcode_url(url: str) -> bool:
    """Return ``True`` when ``url`` is a valid LeetCode problem URL."""
    try:
        extract_leetcode_slug(url)
    except InvalidLeetCodeURLError:
        return False
    return True


def normalize_leetcode_url(slug: str) -> str:
    """Build the canonical LeetCode problem URL for a slug."""
    parsed = urlparse(slug)
    if parsed.scheme:
        return slug
    return f"https://leetcode.com/problems/{slug.strip('/')}/"
