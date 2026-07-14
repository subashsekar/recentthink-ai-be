"""Unit tests for Usage analytics schemas."""

from __future__ import annotations

from app.schemas.admin_internal import (
    AnalyticsDashboardResponse,
    FeatureUsageItem,
    TokenAnalyticsResponse,
)


def test_feature_usage_item_defaults() -> None:
    item = FeatureUsageItem(feature="leetcode", requests=2)
    assert item.tokens == 0
    assert item.average_cost == 0.0


def test_dashboard_schema_accepts_nested_windows() -> None:
    payload = AnalyticsDashboardResponse(
        total_requests=5,
        todays_usage={"requests": 1, "tokens": 10},
        weekly_usage={"requests": 3, "tokens": 30},
        monthly_usage={"requests": 5, "tokens": 50},
    )
    assert payload.todays_usage["requests"] == 1


def test_token_analytics_schema() -> None:
    data = TokenAnalyticsResponse(
        total_tokens=100,
        top_features=[{"feature": "dsa", "requests": 1}],
    )
    assert data.total_tokens == 100
