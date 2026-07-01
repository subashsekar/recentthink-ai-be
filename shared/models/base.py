"""Shared abstract ORM base model."""

from __future__ import annotations

from shared.models.mixins import TimestampMixin


class BaseModel(TimestampMixin):
    """Abstract base with common timestamp fields for all ORM models."""

    __abstract__ = True
