"""AI platform service unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, ExecutionMode, ModuleName, SessionStatus
from app.schemas.ai import ChatRequest, ChatResponse, ModuleResponse, PlannerOutput
from app.services.ai_platform_service import AIPlatformService
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.repository import RecordNotFoundError


@pytest.fixture
def user() -> AuthenticatedUser:
    return AuthenticatedUser(user_id=uuid4(), email="u@example.com", role="USER")


@pytest.fixture
def service() -> AIPlatformService:
    orchestrator = MagicMock()
    orchestrator.execute = AsyncMock(
        return_value=ChatResponse(
            session_id=uuid4(),
            status=SessionStatus.COMPLETED,
            planner=PlannerOutput(
                feature=AIFeature.LEETCODE,
                modules=[ModuleName.TEACHER],
                execution_mode=ExecutionMode.SINGLE_LLM,
            ),
            modules=[],
        ),
    )
    history = MagicMock()
    session_repo = MagicMock()
    llm = MagicMock()
    llm._settings.openrouter_model = "openai/gpt-4o-mini"
    llm.list_configured_models.return_value = ["openai/gpt-4o-mini"]
    return AIPlatformService(
        orchestrator=orchestrator,
        history_manager=history,
        session_repo=session_repo,
        llm_client=llm,
    )


@pytest.mark.asyncio
async def test_chat_delegates_to_orchestrator(user: AuthenticatedUser, service: AIPlatformService) -> None:
    request = ChatRequest(feature=AIFeature.LEETCODE, message="Hello")
    response = await service.chat(user, request)
    assert response.status == SessionStatus.COMPLETED
    service._orchestrator.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_validates_session_access(user: AuthenticatedUser, service: AIPlatformService) -> None:
    session_id = uuid4()
    other_owner = uuid4()
    session = MagicMock()
    session.user_id = other_owner
    service._sessions.get_by_id.return_value = session

    request = ChatRequest(feature=AIFeature.LEETCODE, message="Hi", session_id=session_id)
    with pytest.raises(ForbiddenError):
        await service.chat(user, request)


@pytest.mark.asyncio
async def test_chat_missing_session(user: AuthenticatedUser, service: AIPlatformService) -> None:
    service._sessions.get_by_id.return_value = None
    request = ChatRequest(feature=AIFeature.LEETCODE, message="Hi", session_id=uuid4())
    with pytest.raises(RecordNotFoundError):
        await service.chat(user, request)


def test_list_models(service: AIPlatformService) -> None:
    result = service.list_models()
    assert result.default_model == "openai/gpt-4o-mini"
    assert len(result.models) == 1
