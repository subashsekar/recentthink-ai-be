"""Rate limit tests for expensive LeetCode endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.agents.leetcode.dependencies import get_leetcode_service
from app.agents.leetcode.schemas import FollowUpResponse, ManualInputRequiredResponse
from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.main import app
from app.models.enums import SessionStatus


def test_leetcode_analyze_rate_limit_returns_429() -> None:
    """Exceeding the per-IP limit on /leetcode/analyze returns HTTP 429."""
    from app.core.rate_limit import limiter

    user = AuthenticatedUser(user_id=uuid4(), email="user@example.com", role="USER")
    mock_service = MagicMock()
    mock_service.analyze = AsyncMock(
        return_value=ManualInputRequiredResponse(
            session_id=uuid4(),
            status=SessionStatus.MANUAL_REQUIRED,
            message="manual",
            instructions=["paste"],
        ),
    )

    app.dependency_overrides[require_authenticated_user] = lambda: user
    app.dependency_overrides[get_leetcode_service] = lambda: mock_service

    original = limiter.enabled
    limiter.reset()
    limiter.enabled = True
    client = TestClient(app)
    try:
        statuses = [
            client.post(
                "/leetcode/analyze",
                json={"problem_url": "https://leetcode.com/problems/two-sum/"},
                headers={"Authorization": "Bearer fake-token"},
            ).status_code
            for _ in range(32)
        ]
    finally:
        limiter.enabled = original
        limiter.reset()
        app.dependency_overrides.clear()

    assert 429 in statuses
    assert statuses.count(200) <= 30


def test_leetcode_follow_up_rate_limit_returns_429() -> None:
    """Exceeding the per-IP limit on /leetcode/follow-up returns HTTP 429."""
    from app.core.rate_limit import limiter

    user = AuthenticatedUser(user_id=uuid4(), email="user@example.com", role="USER")
    mock_service = MagicMock()
    mock_service.follow_up = AsyncMock(
        return_value=FollowUpResponse(
            session_id=uuid4(),
            intent="hint",
            teacher="Try using a hash map.",
            input_tokens=1,
            output_tokens=1,
            total_tokens=2,
            latency_ms=10,
            execution_time_ms=20,
        ),
    )

    app.dependency_overrides[require_authenticated_user] = lambda: user
    app.dependency_overrides[get_leetcode_service] = lambda: mock_service

    original = limiter.enabled
    limiter.reset()
    limiter.enabled = True
    client = TestClient(app)
    payload = {
        "session_id": str(uuid4()),
        "question": "Can you explain the hash map approach?",
    }
    try:
        statuses = [
            client.post(
                "/leetcode/follow-up",
                json=payload,
                headers={"Authorization": "Bearer fake-token"},
            ).status_code
            for _ in range(62)
        ]
    finally:
        limiter.enabled = original
        limiter.reset()
        app.dependency_overrides.clear()

    assert 429 in statuses
    assert statuses.count(200) <= 60
