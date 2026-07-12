"""HackerRank URL validation and slug extraction utilities."""

from __future__ import annotations

import re

HACKERRANK_CHALLENGE_PATTERN = re.compile(
    r"^https?://(?:www\.)?hackerrank\.com/"
    r"(?:(?:domains/.+?/challenges/)|(?:challenges/))"
    r"(?P<slug>[a-z0-9_-]+)"
    r"(?:/problem|/problem/|/discussion|/editorial|/submissions|/hackerank)?/?(?:\?.*)?$",
    re.IGNORECASE,
)


class InvalidHackerRankURLError(ValueError):
    """Raised when a URL is not a valid HackerRank challenge link."""


def extract_hackerrank_slug(url: str) -> str:
    """Extract the challenge slug from a HackerRank URL."""
    normalized = url.strip()
    match = HACKERRANK_CHALLENGE_PATTERN.match(normalized)
    if not match:
        raise InvalidHackerRankURLError(
            "Invalid HackerRank URL. Expected format: "
            "https://www.hackerrank.com/challenges/<challenge-slug>/problem",
        )
    return match.group("slug")


def is_valid_hackerrank_url(url: str) -> bool:
    """Return ``True`` when ``url`` is a valid HackerRank challenge URL."""
    try:
        extract_hackerrank_slug(url)
    except InvalidHackerRankURLError:
        return False
    return True


def normalize_hackerrank_url(slug: str) -> str:
    """Build the canonical HackerRank challenge URL for a slug."""
    slug = slug.strip().strip("/")
    if slug.lower().startswith("http://") or slug.lower().startswith("https://"):
        return slug
    return f"https://www.hackerrank.com/challenges/{slug}/problem"

