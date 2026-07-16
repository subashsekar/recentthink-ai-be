"""Single-LLM AI platform orchestrator — delegates to LangGraph workflow engine."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from collections.abc import Awaitable, Callable
from uuid import UUID

from app.agents.shared.workflow.graph import AIWorkflowEngine
from app.agents.shared.workflow.nodes import WorkflowNodes
from app.cache import CacheManager
from app.clients.openrouter import OpenRouterClient
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.execution_trace import ExecutionTraceService
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker


class AIPlatformOrchestrator:
    """Coordinates planner → single LLM → processing modules via LangGraph."""

    def __init__(
        self,
        *,
        llm_client: OpenRouterClient | None = None,
        prompt_loader: PromptLoader | None = None,
        session_repo: AISessionRepository | None = None,
        message_repo: AIMessageRepository | None = None,
        execution_trace: ExecutionTraceService | None = None,
        memory_service: ConversationMemoryService | None = None,
        usage_tracker: UsageTracker | None = None,
        cache_manager: CacheManager | None = None,
        workflow_engine: AIWorkflowEngine | None = None,
        teacher: Any | None = None,
        coder: Any | None = None,
        evaluator: Any | None = None,
    ) -> None:
        if workflow_engine is not None:
            self._engine = workflow_engine
        else:
            nodes = WorkflowNodes(
                teacher=teacher,
                coder=coder,
                evaluator=evaluator,
                llm_client=llm_client,
                prompt_loader=prompt_loader,
                session_repo=session_repo,
                message_repo=message_repo,
                execution_trace=execution_trace,
                memory_service=memory_service,
                usage_tracker=usage_tracker,
                cache_manager=cache_manager,
            )
            self._engine = AIWorkflowEngine(nodes=nodes)

    async def execute(
        self,
        *,
        user_id: UUID,
        request: ChatRequest,
    ) -> ChatResponse:
        return await self._engine.execute(user_id=user_id, request=request)

    async def execute_stream(
        self,
        *,
        user_id: UUID,
        request: ChatRequest,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
    ):
        async for event in self._engine.execute_stream(
            user_id=user_id,
            request=request,
            cancel_check=cancel_check,
        ):
            yield event
