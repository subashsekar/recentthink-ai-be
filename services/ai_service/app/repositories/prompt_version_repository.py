"""Prompt version repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.models.prompt_version import PromptVersion
from shared.exceptions.repository import RecordNotFoundError, RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class PromptVersionRepository:
    """Repository for :class:`PromptVersion` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, prompt_id: UUID) -> PromptVersion | None:
        return self._db.get(PromptVersion, prompt_id)

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

    def list_all(self, *, limit: int = 200, offset: int = 0) -> list[PromptVersion]:
        stmt = (
            select(PromptVersion)
            .order_by(PromptVersion.feature, PromptVersion.module_name, desc(PromptVersion.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(self._db.scalars(stmt).all())

    def list_by_feature(
        self,
        feature: str,
        *,
        module_name: str | None = None,
        locale: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[PromptVersion]:
        stmt = select(PromptVersion).where(PromptVersion.feature == feature)
        if module_name is not None:
            stmt = stmt.where(PromptVersion.module_name == module_name)
        if locale is not None:
            stmt = stmt.where(PromptVersion.locale == locale)
        stmt = stmt.order_by(PromptVersion.module_name, desc(PromptVersion.created_at)).limit(limit).offset(offset)
        return list(self._db.scalars(stmt).all())

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
            if is_active:
                self._deactivate_siblings(
                    feature=feature,
                    module_name=module_name,
                    locale=locale,
                    except_id=prompt.id if prompt.id else None,
                )
            self._db.commit()
            self._db.refresh(prompt)
            return prompt
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to upsert prompt version: %s", exc)
            raise RepositoryError("Failed to save prompt version.") from exc

    def activate(self, prompt_id: UUID) -> PromptVersion:
        prompt = self.get_by_id(prompt_id)
        if prompt is None:
            raise RecordNotFoundError(f"Prompt version '{prompt_id}' not found.")
        try:
            self._deactivate_siblings(
                feature=prompt.feature,
                module_name=prompt.module_name,
                locale=prompt.locale,
                except_id=prompt.id,
            )
            prompt.is_active = True
            self._db.commit()
            self._db.refresh(prompt)
            return prompt
        except RecordNotFoundError:
            raise
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to activate prompt version: %s", exc)
            raise RepositoryError("Failed to activate prompt version.") from exc

    def _deactivate_siblings(
        self,
        *,
        feature: str,
        module_name: str,
        locale: str,
        except_id: UUID | None,
    ) -> None:
        stmt = (
            update(PromptVersion)
            .where(
                PromptVersion.feature == feature,
                PromptVersion.module_name == module_name,
                PromptVersion.locale == locale,
                PromptVersion.is_active.is_(True),
            )
            .values(is_active=False)
        )
        if except_id is not None:
            stmt = stmt.where(PromptVersion.id != except_id)
        self._db.execute(stmt)
