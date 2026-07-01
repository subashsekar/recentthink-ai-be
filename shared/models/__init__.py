"""Shared ORM building blocks."""

from shared.models.base import BaseModel
from shared.models.mixins import TimestampMixin

__all__ = ["BaseModel", "TimestampMixin"]
