"""Service dependency providers."""

from __future__ import annotations

from app.agents.shared.orchestrator.platform_orchestrator import AIPlatformOrchestrator
from app.clients.openrouter import OpenRouterClient
from app.clients.usage import UsageServiceClient
from app.repositories.agent_execution_repository import AgentExecutionRepository
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.conversation_memory_repository import ConversationMemoryRepository
from app.repositories.model_usage_repository import ModelUsageRepository
from app.repositories.prompt_version_repository import PromptVersionRepository
from app.services.ai_platform_service import AIPlatformService
from app.services.models.model_registry import ModelRegistry, get_model_registry
from app.services.execution_trace import ExecutionTraceService
from app.services.followup.followup_service import FollowUpService
from app.services.history.history_manager import HistoryManager
from app.services.memory.conversation_memory import ConversationMemoryService
from app.services.prompt_loader import PromptLoader
from app.services.usage.usage_tracker import UsageTracker
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db

__all__ = ["get_ai_platform_service", "get_model_registry"]


def get_ai_platform_service(db: Session = Depends(get_db)) -> AIPlatformService:
    session_repo = AISessionRepository(db)
    message_repo = AIMessageRepository(db)
    execution_repo = AgentExecutionRepository(db)
    memory_repo = ConversationMemoryRepository(db)
    model_usage_repo = ModelUsageRepository(db)
    prompt_repo = PromptVersionRepository(db)

    llm_client = OpenRouterClient()
    prompt_loader = PromptLoader(prompt_repo=prompt_repo)
    memory_service = ConversationMemoryService(memory_repo)
    usage_tracker = UsageTracker(
        usage_client=UsageServiceClient(),
        model_usage_repo=model_usage_repo,
    )
    orchestrator = AIPlatformOrchestrator(
        llm_client=llm_client,
        prompt_loader=prompt_loader,
        session_repo=session_repo,
        message_repo=message_repo,
        execution_trace=ExecutionTraceService(execution_repo),
        memory_service=memory_service,
        usage_tracker=usage_tracker,
    )
    history_manager = HistoryManager(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_repo=memory_repo,
    )
    followup_service = FollowUpService(
        session_repo=session_repo,
        message_repo=message_repo,
        memory_service=memory_service,
        llm_client=llm_client,
        prompt_loader=prompt_loader,
        usage_tracker=usage_tracker,
    )
    return AIPlatformService(
        orchestrator=orchestrator,
        history_manager=history_manager,
        session_repo=session_repo,
        followup_service=followup_service,
        memory_service=memory_service,
        llm_client=llm_client,
        model_registry=get_model_registry(),
    )
