"""Execution trace service unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.models.enums import AgentRunStatus, ModuleName
from app.services.execution_trace import ExecutionTraceService


def test_record_execution() -> None:
    repo = MagicMock()
    service = ExecutionTraceService(repo)
    session_id = uuid4()
    service.record(
        session_id=session_id,
        module_name=ModuleName.PLANNER,
        status=AgentRunStatus.SUCCESS,
        execution_time_ms=10,
    )
    repo.create_execution.assert_called_once()


@pytest.mark.asyncio
async def test_trace_async_success() -> None:
    repo = MagicMock()
    service = ExecutionTraceService(repo)

    async def runner() -> str:
        return "ok"

    result = await service.trace_async(
        session_id=uuid4(),
        module_name=ModuleName.LLM,
        runner=runner,
    )
    assert result == "ok"
    repo.create_execution.assert_called_once()


@pytest.mark.asyncio
async def test_trace_async_failure() -> None:
    repo = MagicMock()
    service = ExecutionTraceService(repo)

    async def runner() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await service.trace_async(
            session_id=uuid4(),
            module_name=ModuleName.LLM,
            runner=runner,
        )
    repo.create_execution.assert_called_once()
