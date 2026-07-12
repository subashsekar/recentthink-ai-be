"""Repository dependency providers."""

from __future__ import annotations

from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.course_repository import CourseProgressRepository, CourseRepository
from app.repositories.dsa_pattern_repository import PatternProgressRepository, PatternSessionRepository
from app.repositories.hackerrank_progress_repository import HackerrankProgressRepository
from app.repositories.leetcode_progress_repository import LeetCodeProgressRepository
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db

__all__ = [
    "get_ai_message_repository",
    "get_ai_session_repository",
    "get_course_progress_repository",
    "get_course_repository",
    "get_hackerrank_progress_repository",
    "get_leetcode_progress_repository",
    "get_pattern_progress_repository",
    "get_pattern_session_repository",
]


def get_ai_session_repository(
    db: Session = Depends(get_db),
) -> AISessionRepository:
    return AISessionRepository(db)


def get_ai_message_repository(
    db: Session = Depends(get_db),
) -> AIMessageRepository:
    return AIMessageRepository(db)


def get_leetcode_progress_repository(
    db: Session = Depends(get_db),
) -> LeetCodeProgressRepository:
    return LeetCodeProgressRepository(db)


def get_hackerrank_progress_repository(
    db: Session = Depends(get_db),
) -> HackerrankProgressRepository:
    return HackerrankProgressRepository(db)


def get_course_repository(
    db: Session = Depends(get_db),
) -> CourseRepository:
    return CourseRepository(db)


def get_course_progress_repository(
    db: Session = Depends(get_db),
) -> CourseProgressRepository:
    return CourseProgressRepository(db)


def get_pattern_session_repository(
    db: Session = Depends(get_db),
) -> PatternSessionRepository:
    return PatternSessionRepository(db)


def get_pattern_progress_repository(
    db: Session = Depends(get_db),
) -> PatternProgressRepository:
    return PatternProgressRepository(db)
