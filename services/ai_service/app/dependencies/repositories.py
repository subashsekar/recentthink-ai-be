"""Repository dependency providers."""

from __future__ import annotations

from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.leetcode_progress_repository import LeetCodeProgressRepository
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db

__all__ = [
    "get_ai_session_repository",
    "get_leetcode_progress_repository",
]


def get_ai_session_repository(
    db: Session = Depends(get_db),
) -> AISessionRepository:
    return AISessionRepository(db)


def get_leetcode_progress_repository(
    db: Session = Depends(get_db),
) -> LeetCodeProgressRepository:
    return LeetCodeProgressRepository(db)
