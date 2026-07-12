"""DSA Pattern Coach data-access repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.dsa_pattern import PatternBookmark, PatternMastery, PatternProgress, PatternSession
from shared.exceptions.repository import RecordNotFoundError, RepositoryError


class PatternSessionRepository:
    """Persistence for generated DSA pattern sessions and bookmarks."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        title: str,
        pattern_name: str,
        request_payload: dict[str, Any],
        content: dict[str, Any],
        overview: dict[str, Any] | None = None,
        mental_model: dict[str, Any] | None = None,
        recognition: dict[str, Any] | None = None,
        visualization: dict[str, Any] | None = None,
        templates: list | None = None,
        easy_example: dict[str, Any] | None = None,
        medium_example: dict[str, Any] | None = None,
        hard_example: dict[str, Any] | None = None,
        common_mistakes: list | None = None,
        interview_tips: dict[str, Any] | None = None,
        pattern_comparison: list | None = None,
        practice: dict[str, Any] | None = None,
        quiz: dict[str, Any] | None = None,
        next_pattern_recommendation: dict[str, Any] | None = None,
        level: str | None = None,
        language: str | None = None,
        learning_style: str | None = None,
        category: str | None = None,
        difficulty: str | None = None,
        estimated_study_time: str | None = None,
        description: str | None = None,
    ) -> PatternSession:
        row = PatternSession(
            user_id=user_id,
            session_id=session_id,
            title=title,
            pattern_name=pattern_name,
            level=level,
            language=language,
            learning_style=learning_style,
            category=category,
            difficulty=difficulty,
            estimated_study_time=estimated_study_time,
            description=description,
            overview=overview,
            mental_model=mental_model or {},
            recognition=recognition or {},
            visualization=visualization or {},
            templates=templates or [],
            easy_example=easy_example or {},
            medium_example=medium_example or {},
            hard_example=hard_example or {},
            common_mistakes=common_mistakes or [],
            interview_tips=interview_tips or {},
            pattern_comparison=pattern_comparison or [],
            practice=practice or {},
            quiz=quiz or {},
            next_pattern_recommendation=next_pattern_recommendation or {},
            request_payload=request_payload,
            content=content,
        )
        try:
            self._db.add(row)
            self._db.commit()
            self._db.refresh(row)
            return row
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create pattern session.") from exc

    def get_by_id(self, pattern_session_id: UUID) -> PatternSession | None:
        return self._db.scalars(select(PatternSession).where(PatternSession.id == pattern_session_id)).first()

    def get_by_session_id(self, session_id: UUID) -> PatternSession | None:
        return self._db.scalars(select(PatternSession).where(PatternSession.session_id == session_id)).first()

    def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> list[PatternSession]:
        stmt = select(PatternSession).where(PatternSession.user_id == user_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                PatternSession.title.ilike(pattern) | PatternSession.pattern_name.ilike(pattern),
            )
        stmt = stmt.order_by(PatternSession.created_at.desc()).limit(limit).offset(offset)
        return list(self._db.scalars(stmt).all())

    def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(PatternSession).where(PatternSession.user_id == user_id)
        return int(self._db.scalar(stmt) or 0)

    def update_progress(
        self,
        pattern_session_id: UUID,
        *,
        practice_completed_delta: int = 0,
        study_minutes_delta: int = 0,
        quiz_score: float | None = None,
        completion_pct: float | None = None,
        mark_completed: bool = False,
        mark_mastered: bool = False,
    ) -> PatternSession:
        row = self.get_by_id(pattern_session_id)
        if row is None:
            raise RecordNotFoundError(f"Pattern session '{pattern_session_id}' not found.")
        row.practice_completed += practice_completed_delta
        row.study_minutes += study_minutes_delta
        if quiz_score is not None:
            row.quiz_score = quiz_score
        if completion_pct is not None:
            row.completion_pct = completion_pct
        if mark_completed or mark_mastered:
            row.status = "mastered" if mark_mastered else "completed"
            row.completion_pct = 100.0
        try:
            self._db.commit()
            self._db.refresh(row)
            return row
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update pattern session progress.") from exc

    def delete(self, pattern_session_id: UUID) -> None:
        row = self.get_by_id(pattern_session_id)
        if row is None:
            raise RecordNotFoundError(f"Pattern session '{pattern_session_id}' not found.")
        try:
            self._db.delete(row)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to delete pattern session.") from exc

    def add_bookmark(
        self,
        *,
        user_id: UUID,
        pattern_session_id: UUID,
        item_type: str,
        item_id: str,
        title: str | None = None,
    ) -> PatternBookmark:
        bookmark = PatternBookmark(
            user_id=user_id,
            pattern_session_id=pattern_session_id,
            item_type=item_type,
            item_id=item_id,
            title=title,
        )
        try:
            self._db.add(bookmark)
            self._db.commit()
            self._db.refresh(bookmark)
            return bookmark
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create pattern bookmark.") from exc


class PatternProgressRepository:
    """Aggregated per-user DSA pattern progress + mastery."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, user_id: UUID) -> PatternProgress:
        progress = self.get_by_user_id(user_id)
        if progress is not None:
            return progress
        progress = PatternProgress(user_id=user_id, patterns=[], weak_patterns=[], strong_patterns=[])
        try:
            self._db.add(progress)
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create pattern progress.") from exc

    def get_by_user_id(self, user_id: UUID) -> PatternProgress | None:
        return self._db.scalars(select(PatternProgress).where(PatternProgress.user_id == user_id)).first()

    def record_pattern_learned(
        self,
        user_id: UUID,
        *,
        pattern_name: str,
        next_pattern: str | None = None,
    ) -> PatternProgress:
        progress = self.get_or_create(user_id)
        now = datetime.now(tz=UTC)
        patterns = list(progress.patterns or [])
        if pattern_name not in patterns:
            patterns.append(pattern_name)
            progress.patterns_learned += 1
        progress.patterns = patterns
        if next_pattern:
            progress.recommended_next_pattern = next_pattern
        self._bump_streak(progress, now)
        self._upsert_mastery(user_id, pattern_name, sessions_delta=1)
        try:
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update pattern progress.") from exc

    def apply_deltas(
        self,
        user_id: UUID,
        *,
        pattern_name: str | None = None,
        practice_completed_delta: int = 0,
        quizzes_completed_delta: int = 0,
        quiz_score: float | None = None,
        study_minutes_delta: int = 0,
        mark_mastered: bool = False,
        weak_patterns: list[str] | None = None,
        strong_patterns: list[str] | None = None,
        recommended_next_pattern: str | None = None,
    ) -> PatternProgress:
        progress = self.get_or_create(user_id)
        now = datetime.now(tz=UTC)
        progress.practice_completed += practice_completed_delta
        progress.quizzes_completed += quizzes_completed_delta
        progress.learning_time_minutes += study_minutes_delta
        if quiz_score is not None and progress.quizzes_completed > 0:
            total = progress.average_quiz_score * (progress.quizzes_completed - quizzes_completed_delta)
            progress.average_quiz_score = (total + quiz_score) / max(progress.quizzes_completed, 1)
        if weak_patterns is not None:
            progress.weak_patterns = weak_patterns
        if strong_patterns is not None:
            progress.strong_patterns = strong_patterns
        if recommended_next_pattern:
            progress.recommended_next_pattern = recommended_next_pattern
        if pattern_name:
            self._upsert_mastery(
                user_id,
                pattern_name,
                practice_delta=practice_completed_delta,
                quiz_delta=quizzes_completed_delta,
                quiz_score=quiz_score,
                mark_mastered=mark_mastered,
            )
            if mark_mastered:
                mastery_rows = self.list_mastery(user_id)
                progress.patterns_mastered = sum(1 for m in mastery_rows if m.status == "mastered")
                strong = list(progress.strong_patterns or [])
                if pattern_name not in strong:
                    strong.append(pattern_name)
                progress.strong_patterns = strong
        self._bump_streak(progress, now)
        try:
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update pattern progress.") from exc

    def list_mastery(self, user_id: UUID) -> list[PatternMastery]:
        stmt = (
            select(PatternMastery)
            .where(PatternMastery.user_id == user_id)
            .order_by(PatternMastery.updated_at.desc())
        )
        return list(self._db.scalars(stmt).all())

    def get_mastery(self, user_id: UUID, pattern_name: str) -> PatternMastery | None:
        return self._db.scalars(
            select(PatternMastery).where(
                PatternMastery.user_id == user_id,
                PatternMastery.pattern_name == pattern_name,
            ),
        ).first()

    def _upsert_mastery(
        self,
        user_id: UUID,
        pattern_name: str,
        *,
        sessions_delta: int = 0,
        practice_delta: int = 0,
        quiz_delta: int = 0,
        quiz_score: float | None = None,
        mark_mastered: bool = False,
    ) -> PatternMastery:
        row = self.get_mastery(user_id, pattern_name)
        now = datetime.now(tz=UTC)
        if row is None:
            # Column defaults apply on flush; set counters here so += works pre-flush.
            row = PatternMastery(
                user_id=user_id,
                pattern_name=pattern_name,
                sessions_count=0,
                practice_completed=0,
                quiz_attempts=0,
                best_quiz_score=0.0,
                mastery_pct=0.0,
            )
            self._db.add(row)
        row.sessions_count += sessions_delta
        row.practice_completed += practice_delta
        row.quiz_attempts += quiz_delta
        if quiz_score is not None:
            row.best_quiz_score = max(row.best_quiz_score or 0.0, quiz_score)
        if mark_mastered:
            row.status = "mastered"
            row.mastery_pct = 100.0
        else:
            # Heuristic mastery: sessions + practice + quiz performance.
            score = min(100.0, row.sessions_count * 20 + row.practice_completed * 10 + row.best_quiz_score * 0.4)
            row.mastery_pct = score
            if score >= 80:
                row.status = "mastered"
            elif row.practice_completed > 0 or row.quiz_attempts > 0:
                row.status = "practiced"
            else:
                row.status = "learning"
        row.last_studied_at = now
        return row

    @staticmethod
    def _bump_streak(progress: PatternProgress, now: datetime) -> None:
        if progress.last_activity_at:
            if now.date() - progress.last_activity_at.date() <= timedelta(days=1):
                if now.date() != progress.last_activity_at.date():
                    progress.current_streak += 1
            elif now.date() != progress.last_activity_at.date():
                progress.current_streak = 1
        else:
            progress.current_streak = 1
        progress.longest_streak = max(progress.longest_streak, progress.current_streak)
        progress.last_activity_at = now
