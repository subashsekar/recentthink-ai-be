"""Prompt version ORM model."""

from __future__ import annotations

import uuid
from uuid import UUID

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base
from shared.models import CreatedAtModel


class PromptVersion(CreatedAtModel, Base):
    """Versioned prompt content loaded from files or admin updates."""

    __tablename__ = "prompt_versions"
    __table_args__ = (
        UniqueConstraint(
            "feature",
            "module_name",
            "version",
            "locale",
            name="uq_prompt_versions_feature_module_version_locale",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    feature: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    module_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="en")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
