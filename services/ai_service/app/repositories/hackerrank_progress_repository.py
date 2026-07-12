"""HackerRank progress data-access repository."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.hackerrank_progress import HackerrankProgress
from shared.exceptions.repository import RepositoryError


class HackerrankProgressRepository:
    """Repository for :class:`HackerrankProgress` persistence."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, user_id: UUID) -> HackerrankProgress:
        progress = self.get_by_user_id(user_id)
        if progress is not None:
            return progress
        progress = HackerrankProgress(
            user_id=user_id,
            weak_topics=[],
            strong_topics=[],
            domains=[],
            languages=[],
            tags=[],
        )
        try:
            self._db.add(progress)
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create progress record.") from exc

    def get_by_user_id(self, user_id: UUID) -> HackerrankProgress | None:
        stmt = select(HackerrankProgress).where(HackerrankProgress.user_id == user_id)
        return self._db.scalars(stmt).first()

    def record_attempt(
        self,
        user_id: UUID,
        *,
        difficulty: str | None,
        category: str | None,
        domain: str | None,
        language: str | None,
        tags: list[str] | None,
        completed: bool,
    ) -> HackerrankProgress:
        progress = self.get_or_create(user_id)
        now = datetime.now(tz=UTC)
        progress.problems_attempted += 1
        if completed:
            progress.problems_completed += 1

        diff = (difficulty or "").lower()
        if diff == "easy":
            progress.easy_count += 1
        elif diff == "medium":
            progress.medium_count += 1
        elif diff == "hard":
            progress.hard_count += 1

        weak = list(progress.weak_topics or [])
        strong = list(progress.strong_topics or [])
        if category:
            if completed and category not in strong:
                strong.append(category)
            elif not completed and category not in weak:
                weak.append(category)
        progress.weak_topics = weak
        progress.strong_topics = strong

        domains = list(progress.domains or [])
        if domain and domain not in domains:
            domains.append(domain)
        progress.domains = domains

        langs = list(progress.languages or [])
        if language and language not in langs:
            langs.append(language)
        progress.languages = langs

        tag_list = list(progress.tags or [])
        for t in tags or []:
            if t and t not in tag_list:
                tag_list.append(t)
        progress.tags = tag_list

        if progress.last_activity_at:
            if now.date() - progress.last_activity_at.date() <= timedelta(days=1):
                progress.current_streak += 1
            elif now.date() != progress.last_activity_at.date():
                progress.current_streak = 1
        else:
            progress.current_streak = 1
        progress.longest_streak = max(progress.longest_streak, progress.current_streak)
        progress.last_activity_at = now

        try:
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update progress.") from exc

