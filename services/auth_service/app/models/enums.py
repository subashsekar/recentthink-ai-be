"""Authentication domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    """Authorization role assigned to a user account."""

    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"
