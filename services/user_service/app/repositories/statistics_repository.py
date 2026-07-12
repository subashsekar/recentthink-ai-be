"""Read-only statistics aggregation from AI Service tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shared.exceptions import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class UserStatistics:
    """Aggregated learning statistics for a user."""

    problems_solved: int
    courses_completed: int
    patterns_learned: int
    current_streak: int
    longest_streak: int
    learning_hours: float
    last_active: datetime | None


class StatisticsRepository:
    """Read aggregates from AI-owned progress tables without duplicating rows.

    Queries ``leetcode_progress``, ``hackerrank_progress``, ``course_progress``,
    and ``pattern_progress`` directly. Missing rows are treated as zeros.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_user(self, user_id: UUID) -> UserStatistics:
        """Return combined learning statistics for ``user_id``."""
        try:
            leetcode = self._fetch_one(
                """
                SELECT problems_completed, current_streak, longest_streak, last_activity_at
                FROM leetcode_progress
                WHERE user_id = :uid
                """,
                user_id,
            )
            hackerrank = self._fetch_one(
                """
                SELECT problems_completed, current_streak, longest_streak, last_activity_at
                FROM hackerrank_progress
                WHERE user_id = :uid
                """,
                user_id,
            )
            course = self._fetch_one(
                """
                SELECT courses_completed, learning_streak, longest_streak,
                       study_hours, last_activity_at
                FROM course_progress
                WHERE user_id = :uid
                """,
                user_id,
            )
            pattern = self._fetch_one(
                """
                SELECT patterns_learned, current_streak, longest_streak,
                       learning_time_minutes, last_activity_at
                FROM pattern_progress
                WHERE user_id = :uid
                """,
                user_id,
            )
        except SQLAlchemyError as exc:
            logger.error("Database error loading statistics user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to load statistics.") from exc

        problems_solved = int(leetcode.get("problems_completed") or 0) + int(
            hackerrank.get("problems_completed") or 0
        )
        courses_completed = int(course.get("courses_completed") or 0)
        patterns_learned = int(pattern.get("patterns_learned") or 0)

        streaks = [
            int(leetcode.get("current_streak") or 0),
            int(hackerrank.get("current_streak") or 0),
            int(course.get("learning_streak") or 0),
            int(pattern.get("current_streak") or 0),
        ]
        longest = [
            int(leetcode.get("longest_streak") or 0),
            int(hackerrank.get("longest_streak") or 0),
            int(course.get("longest_streak") or 0),
            int(pattern.get("longest_streak") or 0),
        ]

        study_hours = float(course.get("study_hours") or 0.0)
        pattern_hours = float(pattern.get("learning_time_minutes") or 0) / 60.0
        learning_hours = round(study_hours + pattern_hours, 2)

        last_active_candidates = [
            leetcode.get("last_activity_at"),
            hackerrank.get("last_activity_at"),
            course.get("last_activity_at"),
            pattern.get("last_activity_at"),
        ]
        last_active_values = [ts for ts in last_active_candidates if ts is not None]
        last_active = max(last_active_values) if last_active_values else None

        return UserStatistics(
            problems_solved=problems_solved,
            courses_completed=courses_completed,
            patterns_learned=patterns_learned,
            current_streak=max(streaks),
            longest_streak=max(longest),
            learning_hours=learning_hours,
            last_active=last_active,
        )

    def _fetch_one(self, sql: str, user_id: UUID) -> dict[str, object]:
        row = self._db.execute(text(sql), {"uid": user_id}).mappings().first()
        return dict(row) if row is not None else {}
