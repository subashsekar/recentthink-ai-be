"""Password hashing and verification service."""

from __future__ import annotations

from app.security.password import hash_password, verify_password


class PasswordService:
    """Encapsulates bcrypt password operations."""

    def hash(self, plain_password: str) -> str:
        """Return a bcrypt hash for the given plain-text password."""
        return hash_password(plain_password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Return ``True`` when the plain password matches the stored hash."""
        return verify_password(plain_password, hashed_password)
