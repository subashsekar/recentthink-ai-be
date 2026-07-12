"""Profile field validation helpers."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from shared.exceptions.base import ValidationException

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
_PLATFORM_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9_-]{0,38})$")
_MOBILE_RE = re.compile(r"^\+?[1-9]\d{7,14}$")
_LINKEDIN_HOSTS = frozenset({"linkedin.com", "www.linkedin.com"})


def normalize_optional_text(value: str | None, *, max_length: int | None = None) -> str | None:
    """Trim whitespace; treat blank strings as ``None``."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if max_length is not None and len(cleaned) > max_length:
        raise ValidationException(f"Value exceeds maximum length of {max_length}.")
    return cleaned


def normalize_username(value: str | None) -> str | None:
    """Normalize and validate a public profile username."""
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    cleaned = cleaned.lower()
    if not _USERNAME_RE.fullmatch(cleaned):
        raise ValidationException(
            "Username must be 3-30 characters and contain only letters, digits, "
            "or underscores.",
        )
    return cleaned


def normalize_platform_username(value: str | None, *, field: str) -> str | None:
    """Normalize coding-platform usernames (GitHub / LeetCode / HackerRank)."""
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    cleaned = cleaned.lstrip("@").lower()
    if not _PLATFORM_USERNAME_RE.fullmatch(cleaned):
        raise ValidationException(f"Invalid {field}.")
    return cleaned


def validate_mobile_number(value: str | None) -> str | None:
    """Validate an E.164-ish mobile number (optional leading ``+``)."""
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    digits = re.sub(r"[\s()-]", "", cleaned)
    if not _MOBILE_RE.fullmatch(digits):
        raise ValidationException("Invalid mobile number.")
    return digits


def validate_http_url(value: str | None, *, field: str) -> str | None:
    """Require an absolute ``http``/``https`` URL."""
    cleaned = normalize_optional_text(value)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValidationException(f"Invalid {field}: must be an http(s) URL.")
    return cleaned


def validate_linkedin_url(value: str | None) -> str | None:
    """Validate a LinkedIn profile URL."""
    cleaned = validate_http_url(value, field="linkedin_url")
    if cleaned is None:
        return None
    host = urlparse(cleaned).netloc.lower()
    if host not in _LINKEDIN_HOSTS and not host.endswith(".linkedin.com"):
        raise ValidationException("Invalid linkedin_url: host must be linkedin.com.")
    return cleaned


def validate_bio(value: str | None) -> str | None:
    """Validate optional bio (max 500 characters)."""
    return normalize_optional_text(value, max_length=500)
