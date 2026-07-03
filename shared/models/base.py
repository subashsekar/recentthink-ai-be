"""Shared abstract ORM base model."""

from __future__ import annotations

from shared.models.mixins import CreatedAtMixin, TimestampMixin


class TimestampedModel(TimestampMixin):
    """Abstract ORM base adding common ``created_at``/``updated_at`` columns.

    Named to avoid confusion with Pydantic's ``BaseModel``. Concrete models
    combine this with the SQLAlchemy declarative ``Base``, for example::

        class User(TimestampedModel, Base):
            ...
    """

    __abstract__ = True


class CreatedAtModel(CreatedAtMixin):
    """Abstract ORM base adding only a ``created_at`` column.

    For insert-only records such as one-time tokens::

        class RefreshToken(CreatedAtModel, Base):
            ...
    """

    __abstract__ = True
