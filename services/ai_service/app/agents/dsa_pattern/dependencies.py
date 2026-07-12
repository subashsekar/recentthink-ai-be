"""DSA Pattern Coach dependency providers."""

from __future__ import annotations

from fastapi import Depends

from app.agents.dsa_pattern.agents import PatternAgents
from app.agents.dsa_pattern.service import DsaPatternService
from app.dependencies.repositories import (
    get_ai_message_repository,
    get_ai_session_repository,
    get_pattern_progress_repository,
    get_pattern_session_repository,
)
from app.dependencies.services import get_ai_platform_service
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.dsa_pattern_repository import PatternProgressRepository, PatternSessionRepository
from app.services.ai_platform_service import AIPlatformService


def get_pattern_agents() -> PatternAgents:
    return PatternAgents.create_default()


def get_dsa_pattern_service(
    platform_service: AIPlatformService = Depends(get_ai_platform_service),
    session_repo: AISessionRepository = Depends(get_ai_session_repository),
    pattern_repo: PatternSessionRepository = Depends(get_pattern_session_repository),
    progress_repo: PatternProgressRepository = Depends(get_pattern_progress_repository),
    message_repo: AIMessageRepository = Depends(get_ai_message_repository),
    agents: PatternAgents = Depends(get_pattern_agents),
) -> DsaPatternService:
    return DsaPatternService(
        platform_service=platform_service,
        session_repo=session_repo,
        pattern_repo=pattern_repo,
        progress_repo=progress_repo,
        message_repo=message_repo,
        agents=agents,
    )
