"""Prompt version repository."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.prompt_version import PromptVersion
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class PromptVersionRepository:
    """Repository for :class:`PromptVersion` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(
        self,
        *,
        feature: str,
        module_name: str,
        locale: str = "en",
    ) -> PromptVersion | None:
        stmt = (
            select(PromptVersion)
            .where(
                PromptVersion.feature == feature,
                PromptVersion.module_name == module_name,
                PromptVersion.locale == locale,
                PromptVersion.is_active.is_(True),
            )
            .order_by(desc(PromptVersion.created_at))
            .limit(1)
        )
        return self._db.scalars(stmt).first()

    def upsert_version(
        self,
        *,
        feature: str,
        module_name: str,
        version: str,
        content: str,
        locale: str = "en",
        is_active: bool = True,
    ) -> PromptVersion:
        stmt = select(PromptVersion).where(
            PromptVersion.feature == feature,
            PromptVersion.module_name == module_name,
            PromptVersion.version == version,
            PromptVersion.locale == locale,
        )
        prompt = self._db.scalars(stmt).first()
        if prompt is None:
            prompt = PromptVersion(
                feature=feature,
                module_name=module_name,
                version=version,
                locale=locale,
                content=content,
                is_active=is_active,
            )
            self._db.add(prompt)
        else:
            prompt.content = content
            prompt.is_active = is_active
        try:
            self._db.commit()
            self._db.refresh(prompt)
            return prompt
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to upsert prompt version: %s", exc)
            raise RepositoryError("Failed to save prompt version.") from exc
