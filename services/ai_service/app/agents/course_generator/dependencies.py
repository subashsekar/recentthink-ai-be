"""Course Generator dependency providers."""

from __future__ import annotations

from fastapi import Depends

from app.agents.course_generator.agents import CourseAgents
from app.agents.course_generator.service import CourseGeneratorService
from app.dependencies.repositories import (
    get_ai_message_repository,
    get_ai_session_repository,
    get_course_progress_repository,
    get_course_repository,
)
from app.dependencies.services import get_ai_platform_service
from app.repositories.ai_message_repository import AIMessageRepository
from app.repositories.ai_session_repository import AISessionRepository
from app.repositories.course_repository import CourseProgressRepository, CourseRepository
from app.services.ai_platform_service import AIPlatformService


def get_course_agents() -> CourseAgents:
    return CourseAgents.create_default()


def get_course_generator_service(
    platform_service: AIPlatformService = Depends(get_ai_platform_service),
    session_repo: AISessionRepository = Depends(get_ai_session_repository),
    course_repo: CourseRepository = Depends(get_course_repository),
    progress_repo: CourseProgressRepository = Depends(get_course_progress_repository),
    message_repo: AIMessageRepository = Depends(get_ai_message_repository),
    agents: CourseAgents = Depends(get_course_agents),
) -> CourseGeneratorService:
    return CourseGeneratorService(
        platform_service=platform_service,
        session_repo=session_repo,
        course_repo=course_repo,
        progress_repo=progress_repo,
        message_repo=message_repo,
        agents=agents,
    )
