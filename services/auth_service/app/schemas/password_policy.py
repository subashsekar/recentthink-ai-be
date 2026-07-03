"""Shared password strength rules for API request validation."""

from __future__ import annotations

import re

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128
_PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).+$",
)


def validate_password_strength(value: str) -> str:
    """Enforce minimum password complexity.

    Requires at least one lowercase letter, uppercase letter, digit, and
    special character.
    """
    if len(value) < PASSWORD_MIN_LENGTH:
        msg = f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
        raise ValueError(msg)
    if len(value) > PASSWORD_MAX_LENGTH:
        msg = f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
        raise ValueError(msg)
    if not _PASSWORD_PATTERN.match(value):
        msg = (
            "Password must contain at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
        raise ValueError(msg)
    return value
