"""Repository and service FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from app.repositories.profile_repository import ProfileRepository
from app.repositories.statistics_repository import StatisticsRepository
from app.services.avatar_service import AvatarService
from app.services.profile_service import ProfileService
from app.services.public_profile_service import PublicProfileService
from app.services.statistics_service import StatisticsService
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_profile_repository(db: DbSession) -> ProfileRepository:
    return ProfileRepository(db)


def get_statistics_repository(db: DbSession) -> StatisticsRepository:
    return StatisticsRepository(db)


def get_profile_service(db: DbSession) -> ProfileService:
    return ProfileService(db)


def get_statistics_service(db: DbSession) -> StatisticsService:
    return StatisticsService(db)


def get_avatar_service(db: DbSession) -> AvatarService:
    return AvatarService(db)


def get_public_profile_service(db: DbSession) -> PublicProfileService:
    return PublicProfileService(db)
