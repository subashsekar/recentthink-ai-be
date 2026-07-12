"""Statistics repository unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4


def test_get_for_user_aggregates_sources() -> None:
    from app.repositories.statistics_repository import StatisticsRepository

    db = MagicMock()
    now = datetime(2026, 7, 1, tzinfo=UTC)
    earlier = datetime(2026, 6, 1, tzinfo=UTC)

    rows = [
        {
            "problems_completed": 10,
            "current_streak": 2,
            "longest_streak": 5,
            "last_activity_at": earlier,
        },
        {
            "problems_completed": 3,
            "current_streak": 1,
            "longest_streak": 4,
            "last_activity_at": None,
        },
        {
            "courses_completed": 2,
            "learning_streak": 7,
            "longest_streak": 9,
            "study_hours": 3.5,
            "last_activity_at": now,
        },
        {
            "patterns_learned": 4,
            "current_streak": 3,
            "longest_streak": 6,
            "learning_time_minutes": 90,
            "last_activity_at": earlier,
        },
    ]

    class _Result:
        def __init__(self, row: dict | None) -> None:
            self._row = row

        def mappings(self) -> "_Result":
            return self

        def first(self) -> dict | None:
            return self._row

    db.execute.side_effect = [_Result(row) for row in rows]
    stats = StatisticsRepository(db).get_for_user(uuid4())

    assert stats.problems_solved == 13
    assert stats.courses_completed == 2
    assert stats.patterns_learned == 4
    assert stats.current_streak == 7
    assert stats.longest_streak == 9
    assert stats.learning_hours == 5.0
    assert stats.last_active == now


def test_get_for_user_empty_rows() -> None:
    from app.repositories.statistics_repository import StatisticsRepository

    db = MagicMock()

    class _Result:
        def mappings(self) -> "_Result":
            return self

        def first(self) -> None:
            return None

    db.execute.side_effect = [_Result()] * 4
    stats = StatisticsRepository(db).get_for_user(uuid4())
    assert stats.problems_solved == 0
    assert stats.last_active is None
