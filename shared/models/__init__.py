"""Shared ORM building blocks."""

from shared.models.base import TimestampedModel
from shared.models.mixins import TimestampMixin

__all__ = ["TimestampMixin", "TimestampedModel"]
