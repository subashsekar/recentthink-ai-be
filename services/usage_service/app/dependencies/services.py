"""Usage service dependency providers."""

from __future__ import annotations

from app.repositories.usage_record_repository import UsageRecordRepository
from app.services.usage_service import UsageService
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db


def get_usage_record_repository(
    db: Session = Depends(get_db),
) -> UsageRecordRepository:
    return UsageRecordRepository(db)


def get_usage_service(
    repository: UsageRecordRepository = Depends(get_usage_record_repository),
) -> UsageService:
    return UsageService(repository)
