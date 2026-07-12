"""Profile HTTP routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.repositories import (
    get_avatar_service,
    get_profile_service,
    get_public_profile_service,
    get_statistics_service,
)
from app.schemas.profile import (
    AvatarUploadResponse,
    ProfileResponse,
    ProfileUpdate,
    PublicProfileResponse,
    StatisticsResponse,
)
from app.services.avatar_service import AvatarService
from app.services.profile_service import ProfileService
from app.services.public_profile_service import PublicProfileService
from app.services.statistics_service import StatisticsService
from fastapi import APIRouter, Depends, File, Query, UploadFile

router = APIRouter(prefix="/profile", tags=["profile"])


def _resolve_target_user_id(
    current_user: AuthenticatedUser,
    user_id: UUID | None,
) -> UUID:
    """Owners default to self; admins may target another user via ``user_id``."""
    if user_id is None:
        return current_user.user_id
    return user_id


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
    user_id: UUID | None = Query(
        default=None,
        description="Admin-only: fetch another user's full profile.",
    ),
) -> ProfileResponse:
    """Return the current user's profile (or another user's profile for admins)."""
    target = _resolve_target_user_id(current_user, user_id)
    profile = service.get_profile(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        target_user_id=target,
    )
    return ProfileResponse.model_validate(profile)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdate,
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[ProfileService, Depends(get_profile_service)],
    user_id: UUID | None = Query(
        default=None,
        description="Admin-only: update another user's profile.",
    ),
) -> ProfileResponse:
    """Update the current user's profile (creates on first update if missing)."""
    target = _resolve_target_user_id(current_user, user_id)
    profile = service.update_profile(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        target_user_id=target,
        payload=payload,
    )
    return ProfileResponse.model_validate(profile)


@router.get("/statistics", response_model=StatisticsResponse)
def get_statistics(
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[StatisticsService, Depends(get_statistics_service)],
    user_id: UUID | None = Query(
        default=None,
        description="Admin-only: fetch another user's statistics.",
    ),
) -> StatisticsResponse:
    """Return learning statistics aggregated from other services."""
    target = _resolve_target_user_id(current_user, user_id)
    return service.get_statistics(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        target_user_id=target,
    )


@router.post("/avatar", response_model=AvatarUploadResponse)
async def upload_avatar(
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AvatarService, Depends(get_avatar_service)],
    file: UploadFile = File(...),
    user_id: UUID | None = Query(
        default=None,
        description="Admin-only: upload avatar for another user.",
    ),
) -> AvatarUploadResponse:
    """Upload or replace the profile avatar."""
    target = _resolve_target_user_id(current_user, user_id)
    data = await file.read()
    return service.upload(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        target_user_id=target,
        data=data,
        content_type=file.content_type,
        filename=file.filename,
    )


@router.delete("/avatar", status_code=204)
async def delete_avatar(
    current_user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
    service: Annotated[AvatarService, Depends(get_avatar_service)],
    user_id: UUID | None = Query(
        default=None,
        description="Admin-only: delete avatar for another user.",
    ),
) -> None:
    """Delete the profile avatar."""
    target = _resolve_target_user_id(current_user, user_id)
    service.delete(
        actor_id=current_user.user_id,
        actor_role=current_user.role,
        target_user_id=target,
    )


@router.get("/public/{username}", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    service: Annotated[PublicProfileService, Depends(get_public_profile_service)],
) -> PublicProfileResponse:
    """Return the public profile for ``username`` (no auth required)."""
    return service.get_by_username(username)
