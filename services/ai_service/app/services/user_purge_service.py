"""Best-effort purge of AI-owned rows for a deleted account."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.course import CourseBookmark, CourseProgress
from app.models.dsa_pattern import PatternBookmark, PatternMastery, PatternProgress
from app.models.hackerrank_progress import HackerrankProgress
from app.models.leetcode_progress import LeetCodeProgress
from app.repositories.ai_session_repository import AISessionRepository
from shared.exceptions.repository import RepositoryError
from shared.logging import get_logger

logger = get_logger(__name__)


class UserPurgeService:
    """Delete AI sessions (cascading children) and progress tables for a user."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._sessions = AISessionRepository(db)

    def purge_user(self, user_id: UUID) -> dict[str, int]:
        """Remove all AI data keyed by ``user_id``. Idempotent."""
        try:
            sessions_deleted = self._sessions.delete_by_user(user_id, commit=False)
            # Progress / mastery / bookmark orphans not covered by session CASCADE.
            progress_counts = {
                "leetcode_progress": self._delete_where(LeetCodeProgress, user_id),
                "hackerrank_progress": self._delete_where(HackerrankProgress, user_id),
                "course_progress": self._delete_where(CourseProgress, user_id),
                "pattern_progress": self._delete_where(PatternProgress, user_id),
                "pattern_mastery": self._delete_where(PatternMastery, user_id),
                "course_bookmarks": self._delete_where(CourseBookmark, user_id),
                "pattern_bookmarks": self._delete_where(PatternBookmark, user_id),
            }
            self._db.commit()
            result = {"sessions_deleted": sessions_deleted, **progress_counts}
            logger.info("Purged AI data for user_id=%s %s", user_id, result)
            return result
        except RepositoryError:
            raise
        except Exception as exc:
            self._db.rollback()
            logger.error("Failed to purge AI data for user_id=%s: %s", user_id, exc)
            raise RepositoryError("Failed to purge user AI data.") from exc

    def _delete_where(self, model: type, user_id: UUID) -> int:
        result = self._db.execute(delete(model).where(model.user_id == user_id))
        return int(result.rowcount or 0)
