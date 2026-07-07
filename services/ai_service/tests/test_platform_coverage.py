"""Additional platform coverage tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.clients.openrouter import LLMResponse
from app.clients.usage import UsageServiceClient
from app.dependencies.auth import AuthenticatedUser
from app.models.enums import AIFeature, AgentRunStatus, ModuleName, SessionStatus
from app.schemas.ai import ChatRequest
from app.services.execution_trace import ExecutionTraceService
from app.services.history.history_manager import HistoryManager
from app.services.prompt_loader import PromptLoader
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_usage_client_sends_internal_service_token() -> None:
    settings = MagicMock(
        usage_service_url="http://usage",
        internal_service_token="test-internal-token",
    )
    client = UsageServiceClient(settings=settings)
    with patch("app.clients.usage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        await client.record_usage(
            user_id=uuid4(),
            feature="leetcode",
            token_usage=10,
            execution_time_ms=5,
        )

        mock_client.post.assert_awaited_once()
        _, kwargs = mock_client.post.await_args
        assert kwargs["headers"]["X-Internal-Service-Token"] == "test-internal-token"


@pytest.mark.asyncio
async def test_usage_client_logs_http_error() -> None:
    client = UsageServiceClient(
        settings=MagicMock(
            usage_service_url="http://usage",
            internal_service_token="test-internal-token",
        ),
    )
    with patch("app.clients.usage.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.HTTPError("down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        await client.record_usage(
            user_id=uuid4(),
            feature="leetcode",
            token_usage=10,
            execution_time_ms=5,
        )


def test_execution_trace_sync_failure() -> None:
    repo = MagicMock()
    service = ExecutionTraceService(repo)

    def runner() -> None:
        raise ValueError("fail")

    with pytest.raises(ValueError):
        service.trace_sync(
            session_id=uuid4(),
            module_name=ModuleName.PLANNER,
            runner=runner,
        )
    repo.create_execution.assert_called_once()


def test_prompt_loader_db_override(tmp_path) -> None:
    prompts_root = tmp_path / "shared" / "v1"
    prompts_root.mkdir(parents=True)
    (prompts_root / "single_llm.txt").write_text("file", encoding="utf-8")

    prompt_repo = MagicMock()
    db_prompt = MagicMock()
    db_prompt.content = "db prompt"
    prompt_repo.get_active.return_value = db_prompt

    loader = PromptLoader(prompts_root=tmp_path, prompt_repo=prompt_repo)
    assert loader.load(feature="leetcode", module_name="single_llm") == "db prompt"


@pytest.mark.asyncio
async def test_orchestrator_continues_existing_session() -> None:
    user_id = uuid4()
    session_id = uuid4()
    session = MagicMock()
    session.id = session_id

    session_repo = MagicMock()
    session_repo.get_by_id.return_value = session
    session_repo.update_session.return_value = session

    llm = MagicMock()
    llm.chat_completion = AsyncMock(
        return_value=LLMResponse(
            content='{"teacher":{"explanation":"hi"},"coder":{},"evaluator":{}}',
            model="openai/gpt-4o-mini",
            provider="openai",
            prompt_tokens=1,
            completion_tokens=1,
            latency_ms=1,
            estimated_cost=0.0,
        ),
    )

    prompts = MagicMock()
    prompts.load.return_value = "system"

    orchestrator = AIPlatformOrchestrator(
        llm_client=llm,
        prompt_loader=prompts,
        session_repo=session_repo,
        message_repo=MagicMock(),
    )

    request = ChatRequest(
        feature=AIFeature.DSA,
        message="Explain trees",
        session_id=session_id,
    )
    result = await orchestrator.execute(user_id=user_id, request=request)
    assert result.session_id == session_id
    session_repo.get_by_id.assert_called_once_with(session_id)


def test_history_admin_lists_all_sessions() -> None:
    admin = AuthenticatedUser(user_id=uuid4(), email="a@example.com", role="ADMIN")
    session_repo = MagicMock()
    message_repo = MagicMock()
    session = MagicMock()
    session.id = uuid4()
    session.feature = AIFeature.LEETCODE
    session.title = "T"
    session.status = SessionStatus.COMPLETED
    session.summary = None
    session.created_at = session.updated_at = MagicMock()
    session_repo.list_all.return_value = [session]

    manager = HistoryManager(session_repo=session_repo, message_repo=message_repo)
    result = manager.list_history(admin)
    assert result.total == 1
    session_repo.list_all.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_module_failure_records_trace() -> None:
    user_id = uuid4()
    session = MagicMock()
    session.id = uuid4()

    session_repo = MagicMock()
    session_repo.create_session.return_value = session

    teacher = MagicMock()
    teacher.process.side_effect = RuntimeError("format failed")

    trace_repo = MagicMock()
    orchestrator = AIPlatformOrchestrator(
        teacher=teacher,
        session_repo=session_repo,
        message_repo=MagicMock(),
        execution_trace=ExecutionTraceService(trace_repo),
        llm_client=MagicMock(
            chat_completion=AsyncMock(
                return_value=LLMResponse(
                    content='{"teacher":{},"coder":{},"evaluator":{}}',
                    model="m",
                    provider="p",
                    prompt_tokens=1,
                    completion_tokens=1,
                    latency_ms=1,
                    estimated_cost=0.0,
                ),
            ),
        ),
        prompt_loader=MagicMock(load=MagicMock(return_value="sys")),
    )

    result = await orchestrator.execute(
        user_id=user_id,
        request=ChatRequest(feature=AIFeature.LEETCODE, message="test"),
    )
    assert result.status == SessionStatus.COMPLETED
    assert trace_repo.create_execution.called
