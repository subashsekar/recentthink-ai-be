"""AI platform service unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature
from app.schemas.ai import FollowUpRequest, SummarizeResponse
from app.services.ai_platform_service import AIPlatformService


@pytest.fixture
def platform_service() -> AIPlatformService:
    session = MagicMock()
    session.user_id = uuid4()
    session.feature = AIFeature.LEETCODE

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session

    memory_service = MagicMock()
    memory_service.load.return_value = {
        "recent_messages": [{"role": "user", "content": "hi"}],
        "summary": "old summary",
        "context": {},
        "long_term": [],
        "follow_up_questions": [],
    }

    summarizer = AsyncMock()
    summarizer.summarize.return_value = (
        "New conversation summary.",
        {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30, "latency_ms": 50},
    )

    followup = AsyncMock()

    return AIPlatformService(
        orchestrator=AsyncMock(),
        history_manager=MagicMock(),
        session_repo=session_repo,
        followup_service=followup,
        memory_service=memory_service,
        summarizer=summarizer,
    )


@pytest.mark.asyncio
async def test_summarize_session(platform_service: AIPlatformService) -> None:
    user = AuthenticatedUser(
        user_id=platform_service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    session_id = uuid4()
    result = await platform_service.summarize_session(user, session_id)
    assert isinstance(result, SummarizeResponse)
    assert "summary" in result.summary.lower() or len(result.summary) > 0
    platform_service._memory.save.assert_called_once()


@pytest.mark.asyncio
async def test_follow_up_delegates(platform_service: AIPlatformService) -> None:
    user = AuthenticatedUser(
        user_id=platform_service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    request = FollowUpRequest(session_id=uuid4(), question="Explain again")
    await platform_service.follow_up(user, request)
    platform_service._followup.handle_follow_up.assert_awaited_once()


def test_clear_memory(platform_service: AIPlatformService) -> None:
    user = AuthenticatedUser(
        user_id=platform_service._sessions.get_by_id.return_value.user_id,
        email="u@test.com",
        role="USER",
    )
    session_id = uuid4()
    platform_service.clear_memory(user, session_id)
    platform_service._memory.delete.assert_called_once_with(session_id)
