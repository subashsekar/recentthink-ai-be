"""Usage tracker unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.services.usage.usage_tracker import UsageTracker


@pytest.mark.asyncio
async def test_record_request_persists_local_and_remote() -> None:
    usage_client = MagicMock()
    usage_client.record_usage = AsyncMock()
    model_repo = MagicMock()
    tracker = UsageTracker(usage_client=usage_client, model_usage_repo=model_repo)

    user_id = uuid4()
    session_id = uuid4()
    await tracker.record_request(
        user_id=user_id,
        session_id=session_id,
        feature="leetcode",
        model="openai/gpt-4o-mini",
        provider="openai",
        input_tokens=100,
        output_tokens=50,
        latency_ms=200,
        execution_time_ms=300,
        estimated_cost=0.001,
    )

    model_repo.create_usage.assert_called_once()
    usage_client.record_usage.assert_awaited_once()
