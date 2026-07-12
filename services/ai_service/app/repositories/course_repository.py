"""Course generator data-access repositories."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.course import Course, CourseBookmark, CourseProgress
from shared.exceptions.repository import RecordNotFoundError, RepositoryError


class CourseRepository:
    """Persistence for generated courses and bookmarks."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        title: str,
        request_payload: dict[str, Any],
        content: dict[str, Any],
        overview: dict[str, Any] | None = None,
        roadmap: list | None = None,
        lessons: list | None = None,
        quizzes: list | None = None,
        assignments: list | None = None,
        projects: list | None = None,
        assessments: list | None = None,
        resources: list | None = None,
        learning_tips: list | None = None,
        next_recommendations: list | None = None,
        adaptive: dict[str, Any] | None = None,
        skill: str | None = None,
        goal: str | None = None,
        level: str | None = None,
        target_level: str | None = None,
        duration_days: int | None = None,
        daily_hours: float | None = None,
        learning_style: str | None = None,
        language: str | None = None,
        programming_language: str | None = None,
        difficulty: str | None = None,
        description: str | None = None,
    ) -> Course:
        course = Course(
            user_id=user_id,
            session_id=session_id,
            title=title,
            skill=skill,
            goal=goal,
            level=level,
            target_level=target_level,
            duration_days=duration_days,
            daily_hours=daily_hours,
            learning_style=learning_style,
            language=language,
            programming_language=programming_language,
            difficulty=difficulty,
            description=description,
            overview=overview,
            roadmap=roadmap or [],
            lessons=lessons or [],
            quizzes=quizzes or [],
            assignments=assignments or [],
            projects=projects or [],
            assessments=assessments or [],
            resources=resources or [],
            learning_tips=learning_tips or [],
            next_recommendations=next_recommendations or [],
            adaptive=adaptive or {},
            request_payload=request_payload,
            content=content,
        )
        try:
            self._db.add(course)
            self._db.commit()
            self._db.refresh(course)
            return course
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create course.") from exc

    def get_by_id(self, course_id: UUID) -> Course | None:
        return self._db.scalars(select(Course).where(Course.id == course_id)).first()

    def get_by_session_id(self, session_id: UUID) -> Course | None:
        return self._db.scalars(select(Course).where(Course.session_id == session_id)).first()

    def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> list[Course]:
        stmt = select(Course).where(Course.user_id == user_id)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(Course.title.ilike(pattern) | Course.skill.ilike(pattern) | Course.goal.ilike(pattern))
        stmt = stmt.order_by(Course.created_at.desc()).limit(limit).offset(offset)
        return list(self._db.scalars(stmt).all())

    def count_by_user(self, user_id: UUID) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Course).where(Course.user_id == user_id)
        return int(self._db.scalar(stmt) or 0)

    def update_progress(
        self,
        course_id: UUID,
        *,
        current_week: int | None = None,
        current_lesson: int | None = None,
        lessons_completed_delta: int = 0,
        quizzes_completed_delta: int = 0,
        projects_completed_delta: int = 0,
        study_hours_delta: float = 0.0,
        completion_pct: float | None = None,
        mark_completed: bool = False,
    ) -> Course:
        course = self.get_by_id(course_id)
        if course is None:
            raise RecordNotFoundError(f"Course '{course_id}' not found.")
        if current_week is not None:
            course.current_week = current_week
        if current_lesson is not None:
            course.current_lesson = current_lesson
        course.lessons_completed += lessons_completed_delta
        course.quizzes_completed += quizzes_completed_delta
        course.projects_completed += projects_completed_delta
        course.study_hours += study_hours_delta
        if completion_pct is not None:
            course.completion_pct = completion_pct
        if mark_completed:
            course.status = "completed"
            course.completion_pct = 100.0
        try:
            self._db.commit()
            self._db.refresh(course)
            return course
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update course progress.") from exc

    def delete(self, course_id: UUID) -> None:
        course = self.get_by_id(course_id)
        if course is None:
            raise RecordNotFoundError(f"Course '{course_id}' not found.")
        try:
            self._db.delete(course)
            self._db.commit()
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to delete course.") from exc

    def add_bookmark(
        self,
        *,
        user_id: UUID,
        course_id: UUID,
        item_type: str,
        item_id: str,
        title: str | None = None,
    ) -> CourseBookmark:
        bookmark = CourseBookmark(
            user_id=user_id,
            course_id=course_id,
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
            raise RepositoryError("Failed to create bookmark.") from exc

    def list_bookmarks(self, user_id: UUID, course_id: UUID | None = None) -> list[CourseBookmark]:
        stmt = select(CourseBookmark).where(CourseBookmark.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(CourseBookmark.course_id == course_id)
        return list(self._db.scalars(stmt.order_by(CourseBookmark.created_at.desc())).all())


class CourseProgressRepository:
    """Aggregated per-user course progress."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, user_id: UUID) -> CourseProgress:
        progress = self.get_by_user_id(user_id)
        if progress is not None:
            return progress
        progress = CourseProgress(user_id=user_id, skills=[])
        try:
            self._db.add(progress)
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to create course progress.") from exc

    def get_by_user_id(self, user_id: UUID) -> CourseProgress | None:
        return self._db.scalars(select(CourseProgress).where(CourseProgress.user_id == user_id)).first()

    def record_course_created(
        self,
        user_id: UUID,
        *,
        skill: str | None,
        duration_days: int | None = None,
        daily_hours: float | None = None,
    ) -> CourseProgress:
        progress = self.get_or_create(user_id)
        now = datetime.now(tz=UTC)
        progress.courses_created += 1
        if skill:
            skills = list(progress.skills or [])
            if skill not in skills:
                skills.append(skill)
            progress.skills = skills
            progress.favorite_skill = skill
        if duration_days and daily_hours:
            progress.study_hours += float(duration_days) * float(daily_hours) * 0.0  # planned, not logged yet
        self._bump_streak(progress, now)
        try:
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update course progress.") from exc

    def apply_deltas(
        self,
        user_id: UUID,
        *,
        lessons_completed_delta: int = 0,
        quizzes_completed_delta: int = 0,
        projects_completed_delta: int = 0,
        study_hours_delta: float = 0.0,
        current_week: int | None = None,
        current_lesson: int | None = None,
        completion_pct: float | None = None,
        mark_course_completed: bool = False,
    ) -> CourseProgress:
        progress = self.get_or_create(user_id)
        now = datetime.now(tz=UTC)
        progress.lessons_completed += lessons_completed_delta
        progress.quizzes_completed += quizzes_completed_delta
        progress.projects_completed += projects_completed_delta
        progress.study_hours += study_hours_delta
        if current_week is not None:
            progress.current_week = current_week
        if current_lesson is not None:
            progress.current_lesson = current_lesson
        if completion_pct is not None:
            progress.completion_pct = completion_pct
        if mark_course_completed:
            progress.courses_completed += 1
            progress.completion_pct = 100.0
        self._bump_streak(progress, now)
        try:
            self._db.commit()
            self._db.refresh(progress)
            return progress
        except Exception as exc:
            self._db.rollback()
            raise RepositoryError("Failed to update course progress.") from exc

    @staticmethod
    def _bump_streak(progress: CourseProgress, now: datetime) -> None:
        if progress.last_activity_at:
            if now.date() - progress.last_activity_at.date() <= timedelta(days=1):
                if now.date() != progress.last_activity_at.date():
                    progress.learning_streak += 1
            elif now.date() != progress.last_activity_at.date():
                progress.learning_streak = 1
        else:
            progress.learning_streak = 1
        progress.longest_streak = max(progress.longest_streak, progress.learning_streak)
        progress.last_activity_at = now
