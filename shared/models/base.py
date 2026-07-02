"""Shared abstract ORM base model."""

from __future__ import annotations

from shared.models.mixins import TimestampMixin


class TimestampedModel(TimestampMixin):
    """Abstract ORM base adding common ``created_at``/``updated_at`` columns.

    Named to avoid confusion with Pydantic's ``BaseModel``. Concrete models
    combine this with the SQLAlchemy declarative ``Base``, for example::

        class User(TimestampedModel, Base):
            ...
    """

    __abstract__ = True
