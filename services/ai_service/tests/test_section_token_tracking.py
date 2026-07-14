"""Section token estimation unit tests (Usage/Admin path)."""

from __future__ import annotations

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.usage.usage_tracker import UsageTracker


@pytest.mark.asyncio
async def test_record_request_forwards_section_tokens() -> None:
    usage_client = MagicMock()
    usage_client.record_usage = AsyncMock()
    tracker = UsageTracker(usage_client=usage_client, model_usage_repo=None)

    await tracker.record_request(
        user_id=uuid4(),
        session_id=uuid4(),
        feature="leetcode",
        model="openai/gpt-4o-mini",
        provider="openai",
        input_tokens=10,
        output_tokens=20,
        latency_ms=5,
        execution_time_ms=10,
        estimated_cost=0.001,
        section_tokens={"teacher": 12, "coder": 8},
    )

    kwargs = usage_client.record_usage.await_args.kwargs
    assert kwargs["section_tokens"] == {"teacher": 12, "coder": 8}
    assert kwargs["prompt_tokens"] == 10
    assert kwargs["completion_tokens"] == 20
