"""Refresh token ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.database import Base
from shared.models import CreatedAtModel

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(CreatedAtModel, Base):
    """Long-lived session token stored in the ``refresh_tokens`` table.

    Issued alongside access tokens so clients can obtain new credentials
    without re-authenticating. Revoked tokens remain for audit purposes.

    The ``token`` column stores the SHA-256 hash of the raw refresh token,
    never the raw value itself, so a database compromise cannot expose usable
    session credentials.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
