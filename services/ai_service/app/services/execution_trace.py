"""Execution trace service."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar
from uuid import UUID

from app.models.enums import AgentRunStatus, ModuleName
from app.repositories.agent_execution_repository import AgentExecutionRepository

T = TypeVar("T")


class ExecutionTraceService:
    """Track planner, LLM, and processing module execution in the database."""

    def __init__(self, execution_repo: AgentExecutionRepository) -> None:
        self._executions = execution_repo

    def record(
        self,
        *,
        session_id: UUID,
        module_name: ModuleName,
        status: AgentRunStatus,
        execution_time_ms: int = 0,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        token_usage: int = 0,
        error_message: str | None = None,
        trace_metadata: dict | None = None,
    ) -> None:
        self._executions.create_execution(
            session_id=session_id,
            module_name=module_name,
            status=status,
            execution_time_ms=execution_time_ms,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            token_usage=token_usage,
            error_message=error_message,
            trace_metadata=trace_metadata,
        )

    async def trace_async(
        self,
        *,
        session_id: UUID,
        module_name: ModuleName,
        runner: Callable[[], Awaitable[T]],
        trace_metadata: dict | None = None,
    ) -> T:
        start = time.perf_counter()
        try:
            result = await runner()
            elapsed = int((time.perf_counter() - start) * 1000)
            self.record(
                session_id=session_id,
                module_name=module_name,
                status=AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
                trace_metadata=trace_metadata,
            )
            return result
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self.record(
                session_id=session_id,
                module_name=module_name,
                status=AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc)[:2000],
                trace_metadata=trace_metadata,
            )
            raise

    def trace_sync(
        self,
        *,
        session_id: UUID,
        module_name: ModuleName,
        runner: Callable[[], T],
        trace_metadata: dict | None = None,
        latency_ms: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> T:
        start = time.perf_counter()
        try:
            result = runner()
            elapsed = int((time.perf_counter() - start) * 1000)
            self.record(
                session_id=session_id,
                module_name=module_name,
                status=AgentRunStatus.SUCCESS,
                execution_time_ms=elapsed,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                token_usage=input_tokens + output_tokens,
                trace_metadata=trace_metadata,
            )
            return result
        except Exception as exc:
            elapsed = int((time.perf_counter() - start) * 1000)
            self.record(
                session_id=session_id,
                module_name=module_name,
                status=AgentRunStatus.FAILED,
                execution_time_ms=elapsed,
                error_message=str(exc)[:2000],
                trace_metadata=trace_metadata,
            )
            raise
