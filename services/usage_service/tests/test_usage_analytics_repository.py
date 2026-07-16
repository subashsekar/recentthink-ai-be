"""Tests for usage record creation and analytics repository paths."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


@pytest.fixture
def mock_db() -> MagicMock:
    return MagicMock()


def test_create_record_persists_and_refreshes(mock_db: MagicMock) -> None:
    from app.repositories.usage_record_repository import UsageRecordRepository

    repo = UsageRecordRepository(mock_db)
    user_id = uuid4()
    session_id = uuid4()

    record = repo.create_record(
        user_id=user_id,
        service_name="ai_service",
        feature="leetcode",
        request_count=1,
        token_usage=150,
        execution_time_ms=420,
        session_id=session_id,
        prompt_tokens=100,
        completion_tokens=50,
        model="google/gemini-2.5-flash",
        provider="openrouter",
        estimated_cost=0.001,
        success=True,
        section_tokens={"teacher": 20, "coder": 30},
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(record)
    assert record.user_id == user_id
    assert record.feature == "leetcode"
    assert record.token_usage == 150
    assert record.section_tokens == {"teacher": 20, "coder": 30}


def test_create_record_rolls_back_on_failure(mock_db: MagicMock) -> None:
    from app.repositories.usage_record_repository import UsageRecordRepository
    from shared.exceptions.repository import RepositoryError

    mock_db.commit.side_effect = RuntimeError("db down")
    repo = UsageRecordRepository(mock_db)

    with pytest.raises(RepositoryError):
        repo.create_record(
            user_id=uuid4(),
            service_name="ai_service",
            feature="hackerrank",
            request_count=1,
            token_usage=10,
            execution_time_ms=100,
        )

    mock_db.rollback.assert_called_once()


def test_delete_by_user_commits_rowcount(mock_db: MagicMock) -> None:
    from app.repositories.usage_record_repository import UsageRecordRepository

    result = MagicMock()
    result.rowcount = 3
    mock_db.execute.return_value = result
    repo = UsageRecordRepository(mock_db)
    user_id = uuid4()

    deleted = repo.delete_by_user(user_id)

    assert deleted == 3
    mock_db.execute.assert_called_once()
    mock_db.commit.assert_called_once()


def test_analytics_dashboard_aggregates_windows(mock_db: MagicMock) -> None:
    from app.repositories.usage_analytics_repository import UsageAnalyticsRepository

    repo = UsageAnalyticsRepository(mock_db)
    window = {
        "requests": 10,
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "tokens": 150,
        "cost": 0.05,
        "sessions": 4,
        "average_execution_time_ms": 200.0,
        "active_users": 2,
        "average_tokens_per_request": 15.0,
        "average_cost_per_request": 0.005,
    }
    with (
        patch.object(repo, "_window_totals", return_value=window),
        patch.object(repo, "_top_users", return_value=[{"user_id": uuid4(), "total_tokens": 150}]),
        patch.object(repo, "_top_feature", return_value="leetcode"),
        patch.object(repo, "_top_model", return_value="google/gemini-2.5-flash"),
        patch.object(repo, "_top_provider", return_value="openrouter"),
    ):
        data = repo.analytics_dashboard()

    assert data["total_requests"] == 10
    assert data["total_tokens_used"] == 150
    assert data["todays_usage"]["requests"] == 10
    assert data["most_used_ai_feature"] == "leetcode"
    assert data["most_used_ai_model"] == "google/gemini-2.5-flash"


def test_token_analytics_includes_tops(mock_db: MagicMock) -> None:
    from app.repositories.usage_analytics_repository import UsageAnalyticsRepository

    repo = UsageAnalyticsRepository(mock_db)
    window = {
        "requests": 5,
        "prompt_tokens": 80,
        "completion_tokens": 40,
        "tokens": 120,
        "cost": 0.02,
        "sessions": 2,
        "average_execution_time_ms": 100.0,
        "active_users": 1,
        "average_tokens_per_request": 24.0,
        "average_cost_per_request": 0.004,
    }
    with (
        patch.object(repo, "_window_totals", return_value=window),
        patch.object(repo, "_top_users", return_value=[]),
        patch.object(
            repo,
            "_feature_breakdown",
            return_value=[{"feature": "dsa_pattern", "requests": 2, "tokens": 40}],
        ),
        patch.object(repo, "_model_breakdown", return_value=[]),
        patch.object(repo, "_provider_breakdown", return_value=[]),
        patch.object(repo, "_section_token_totals", return_value={"teacher": 10}),
        patch.object(repo, "_now", return_value=datetime(2026, 7, 16, tzinfo=UTC)),
        patch.object(
            repo,
            "_start_of_day",
            return_value=datetime(2026, 7, 16, tzinfo=UTC),
        ),
    ):
        data = repo.token_analytics()

    assert data["total_prompt_tokens"] == 80
    assert data["total_completion_tokens"] == 40
    assert data["total_tokens"] == 120
    assert data["section_token_totals"]["teacher"] == 10
    assert data["top_features"][0]["feature"] == "dsa_pattern"


def test_feature_analytics_fills_known_features(mock_db: MagicMock) -> None:
    from app.repositories.usage_analytics_repository import UsageAnalyticsRepository

    repo = UsageAnalyticsRepository(mock_db)
    with patch.object(
        repo,
        "_feature_breakdown",
        return_value=[
            {
                "feature": "leetcode",
                "requests": 3,
                "tokens": 90,
                "cost": 0.01,
                "average_time_ms": 100.0,
                "average_tokens": 30.0,
                "average_cost": 0.003,
            },
        ],
    ):
        data = repo.feature_analytics()

    features = {item["feature"]: item for item in data["items"]}
    assert features["leetcode"]["requests"] == 3
    assert features["hackerrank"]["requests"] == 0
    assert features["course_generator"]["requests"] == 0
    assert "interview" in features
