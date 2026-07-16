"""Feature flag service."""

from __future__ import annotations

from uuid import UUID

from app.models.enums import AuditAction
from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.schemas.admin import (
    FeatureFlagCreate,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
)
from app.services.audit_service import AuditService
from shared.exceptions.base import ValidationException


class FeatureFlagService:
    def __init__(
        self,
        *,
        repository: FeatureFlagRepository,
        audit_service: AuditService,
    ) -> None:
        self._repo = repository
        self._audit = audit_service

    def list(self, *, page: int = 1, page_size: int = 50) -> FeatureFlagListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        skip = (page - 1) * page_size
        rows, total = self._repo.list(skip=skip, limit=page_size)
        return FeatureFlagListResponse(
            items=[FeatureFlagResponse.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_by_key(self, key: str) -> FeatureFlagResponse:
        row = self._repo.require_by_key(key)
        return FeatureFlagResponse.model_validate(row)

    def create(
        self,
        payload: FeatureFlagCreate,
        *,
        actor_id: UUID,
    ) -> FeatureFlagResponse:
        if self._repo.get_by_key(payload.key) is not None:
            raise ValidationException(
                f"Feature flag with key '{payload.key}' already exists."
            )
        row = self._repo.create(
            key=payload.key,
            name=payload.name,
            description=payload.description,
            enabled=payload.enabled,
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.FEATURE_FLAG_CREATED.value,
            reason=payload.key,
            metadata={
                "key": payload.key,
                "name": payload.name,
                "enabled": payload.enabled,
            },
        )
        return FeatureFlagResponse.model_validate(row)

    def update(
        self,
        key: str,
        payload: FeatureFlagUpdate,
        *,
        actor_id: UUID,
    ) -> FeatureFlagResponse:
        row = self._repo.require_by_key(key)
        updates = payload.model_dump(exclude_unset=True)
        row = self._repo.update(
            row,
            name=updates.get("name"),
            description=updates.get("description"),
            enabled=updates.get("enabled"),
        )
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.FEATURE_FLAG_UPDATED.value,
            reason=key,
            metadata={"key": key, "updates": updates},
        )
        return FeatureFlagResponse.model_validate(row)

    def delete(self, key: str, *, actor_id: UUID) -> None:
        row = self._repo.require_by_key(key)
        self._repo.delete(row)
        self._audit.log(
            admin_id=actor_id,
            action=AuditAction.FEATURE_FLAG_DELETED.value,
            reason=key,
            metadata={"key": key, "name": row.name},
        )
