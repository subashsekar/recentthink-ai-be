"""Password hashing utilities."""

from __future__ import annotations

import bcrypt


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plain-text password."""
    password_bytes = plain_password.encode("utf-8")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return ``True`` when the plain password matches the stored hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
