"""HackerRank agent dependency providers."""

from __future__ import annotations

from fastapi import Depends

from app.agents.hackerrank.agents import HackerrankAgents
from app.agents.hackerrank.service import HackerRankService
from app.dependencies.repositories import get_ai_session_repository, get_hackerrank_progress_repository
from app.dependencies.services import get_ai_platform_service
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.hackerrank_progress_repository import HackerrankProgressRepository
from app.services.ai_platform_service import AIPlatformService


def get_hackerrank_agents() -> HackerrankAgents:
    return HackerrankAgents.create_default()


def get_hackerrank_service(
    platform_service: AIPlatformService = Depends(get_ai_platform_service),
    session_repo: AISessionRepository = Depends(get_ai_session_repository),
    progress_repo: HackerrankProgressRepository = Depends(get_hackerrank_progress_repository),
    agents: HackerrankAgents = Depends(get_hackerrank_agents),
) -> HackerRankService:
    return HackerRankService(
        platform_service=platform_service,
        session_repo=session_repo,
        progress_repo=progress_repo,
        agents=agents,
    )

