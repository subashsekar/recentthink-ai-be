"""Feature flag repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.feature_flag import FeatureFlag
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class FeatureFlagRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list(self, *, skip: int = 0, limit: int = 50) -> tuple[list[FeatureFlag], int]:
        try:
            stmt = select(FeatureFlag)
            count_stmt = select(func.count()).select_from(FeatureFlag)
            total = int(self._db.scalar(count_stmt) or 0)
            rows = list(
                self._db.scalars(
                    stmt.order_by(FeatureFlag.key.asc()).offset(skip).limit(limit)
                ).all()
            )
            return rows, total
        except SQLAlchemyError as exc:
            logger.error("Failed to list feature flags: %s", exc)
            raise RepositoryError("Failed to list feature flags.") from exc

    def get_by_key(self, key: str) -> FeatureFlag | None:
        try:
            return self._db.scalar(select(FeatureFlag).where(FeatureFlag.key == key))
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch feature flag key=%s: %s", key, exc)
            raise RepositoryError("Failed to fetch feature flag.") from exc

    def get_by_id(self, flag_id: UUID) -> FeatureFlag | None:
        try:
            return self._db.scalar(select(FeatureFlag).where(FeatureFlag.id == flag_id))
        except SQLAlchemyError as exc:
            logger.error("Failed to fetch feature flag id=%s: %s", flag_id, exc)
            raise RepositoryError("Failed to fetch feature flag.") from exc

    def create(
        self,
        *,
        key: str,
        name: str,
        description: str | None = None,
        enabled: bool = False,
    ) -> FeatureFlag:
        row = FeatureFlag(
            key=key,
            name=name,
            description=description,
            enabled=enabled,
        )
        try:
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
            return row
        except IntegrityError as exc:
            self._db.rollback()
            logger.error("Duplicate feature flag key=%s: %s", key, exc)
            raise RepositoryError(f"Feature flag with key '{key}' already exists.") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to create feature flag: %s", exc)
            raise RepositoryError("Failed to create feature flag.") from exc

    def update(
        self,
        row: FeatureFlag,
        *,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
    ) -> FeatureFlag:
        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if enabled is not None:
            row.enabled = enabled
        try:
            self._db.commit()
            self._db.refresh(row)
            return row
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to update feature flag key=%s: %s", row.key, exc)
            raise RepositoryError("Failed to update feature flag.") from exc

    def delete(self, row: FeatureFlag) -> None:
        try:
            self._db.delete(row)
            self._db.commit()
        except SQLAlchemyError as exc:
            self._db.rollback()
            logger.error("Failed to delete feature flag key=%s: %s", row.key, exc)
            raise RepositoryError("Failed to delete feature flag.") from exc

    def require_by_key(self, key: str) -> FeatureFlag:
        row = self.get_by_key(key)
        if row is None:
            raise RecordNotFoundError("Feature flag not found.")
        return row
