"""LeetCode agent dependency providers."""

from __future__ import annotations

from app.agents.leetcode.agents import LeetCodeAgents
from app.agents.leetcode.service import LeetCodeService
from app.dependencies.repositories import (
    get_ai_session_repository,
    get_leetcode_progress_repository,
)
from app.dependencies.services import get_ai_platform_service
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.leetcode_progress_repository import LeetCodeProgressRepository
from app.services.ai_platform_service import AIPlatformService
from fastapi import Depends


def get_leetcode_agents() -> LeetCodeAgents:
    """Provide the five declared LeetCode pipeline agents."""
    return LeetCodeAgents.create_default()


def get_leetcode_service(
    platform_service: AIPlatformService = Depends(get_ai_platform_service),
    session_repo: AISessionRepository = Depends(get_ai_session_repository),
    progress_repo: LeetCodeProgressRepository = Depends(get_leetcode_progress_repository),
    agents: LeetCodeAgents = Depends(get_leetcode_agents),
) -> LeetCodeService:
    """Provide a :class:`LeetCodeService` wired to the shared AI platform."""
    return LeetCodeService(
        platform_service=platform_service,
        session_repo=session_repo,
        progress_repo=progress_repo,
        agents=agents,
    )
