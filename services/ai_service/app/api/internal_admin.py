"""Internal admin HTTP routes for AI Service analytics."""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.internal import require_internal_service
from app.repositories.admin_analytics_repository import AdminAnalyticsRepository
from app.repositories.prompt_version_repository import PromptVersionRepository
from app.schemas.admin_internal import (
    AIAnalyticsResponse,
    AIUserHistoryResponse,
    ModelAnalyticsResponse,
    PromptUpsertRequest,
    PromptVersionResponse,
    UserPurgeResponse,
)
from app.services.user_purge_service import UserPurgeService
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/admin", tags=["internal-admin"])


def get_admin_analytics_repository(
    db: Session = Depends(get_db),
) -> AdminAnalyticsRepository:
    return AdminAnalyticsRepository(db)


def get_user_purge_service(db: Session = Depends(get_db)) -> UserPurgeService:
    return UserPurgeService(db)


def get_prompt_version_repository(
    db: Session = Depends(get_db),
) -> PromptVersionRepository:
    return PromptVersionRepository(db)


@router.get(
    "/analytics",
    response_model=AIAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def analytics(
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> AIAnalyticsResponse:
    return AIAnalyticsResponse(**repo.platform_analytics())


@router.get(
    "/models",
    response_model=ModelAnalyticsResponse,
    dependencies=[Depends(require_internal_service)],
)
def models(
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> ModelAnalyticsResponse:
    return ModelAnalyticsResponse(**repo.model_usage_breakdown())


@router.get(
    "/users/{user_id}/history",
    response_model=AIUserHistoryResponse,
    dependencies=[Depends(require_internal_service)],
)
def user_history(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: AdminAnalyticsRepository = Depends(get_admin_analytics_repository),
) -> AIUserHistoryResponse:
    return AIUserHistoryResponse(**repo.user_history(user_id, limit=limit, offset=offset))


@router.delete(
    "/users/{user_id}",
    response_model=UserPurgeResponse,
    dependencies=[Depends(require_internal_service)],
)
def purge_user(
    user_id: UUID,
    service: UserPurgeService = Depends(get_user_purge_service),
) -> UserPurgeResponse:
    """Best-effort purge of AI sessions and progress for a deleted account."""
    counts = service.purge_user(user_id)
    return UserPurgeResponse(user_id=str(user_id), **counts)


@router.get(
    "/prompts",
    response_model=list[PromptVersionResponse],
    dependencies=[Depends(require_internal_service)],
)
def list_prompts(
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: PromptVersionRepository = Depends(get_prompt_version_repository),
) -> list[PromptVersionResponse]:
    return [
        PromptVersionResponse.model_validate(row, from_attributes=True)
        for row in repo.list_all(limit=limit, offset=offset)
    ]


@router.get(
    "/prompts/{feature}/{module_name}",
    response_model=list[PromptVersionResponse],
    dependencies=[Depends(require_internal_service)],
)
def list_prompts_by_feature_module(
    feature: str,
    module_name: str,
    locale: str | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: PromptVersionRepository = Depends(get_prompt_version_repository),
) -> list[PromptVersionResponse]:
    return [
        PromptVersionResponse.model_validate(row, from_attributes=True)
        for row in repo.list_by_feature(
            feature,
            module_name=module_name,
            locale=locale,
            limit=limit,
            offset=offset,
        )
    ]


@router.post(
    "/prompts",
    response_model=PromptVersionResponse,
    dependencies=[Depends(require_internal_service)],
)
def upsert_prompt(
    payload: PromptUpsertRequest,
    repo: PromptVersionRepository = Depends(get_prompt_version_repository),
) -> PromptVersionResponse:
    prompt = repo.upsert_version(
        feature=payload.feature,
        module_name=payload.module_name,
        version=payload.version,
        content=payload.content,
        locale=payload.locale,
        is_active=payload.is_active,
    )
    return PromptVersionResponse.model_validate(prompt, from_attributes=True)


@router.post(
    "/prompts/{prompt_id}/activate",
    response_model=PromptVersionResponse,
    dependencies=[Depends(require_internal_service)],
)
def activate_prompt(
    prompt_id: UUID,
    repo: PromptVersionRepository = Depends(get_prompt_version_repository),
) -> PromptVersionResponse:
    prompt = repo.activate(prompt_id)
    return PromptVersionResponse.model_validate(prompt, from_attributes=True)
