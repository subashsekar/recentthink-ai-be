"""Admin Service dependency providers."""

from __future__ import annotations

from typing import Annotated

from app.clients.ai_client import AIServiceClient
from app.clients.auth_client import AuthServiceClient
from app.clients.usage_client import UsageServiceClient
from app.clients.user_client import UserServiceClient
from app.repositories.audit_repository import AuditRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.audit_service import AuditService
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService
from app.services.system_health_service import SystemHealthService
from app.services.user_management_service import UserManagementService
from app.services.analytics_service import AnalyticsService
from fastapi import Depends
from sqlalchemy.orm import Session

from shared.database import get_db

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_client() -> AuthServiceClient:
    return AuthServiceClient()


def get_user_client() -> UserServiceClient:
    return UserServiceClient()


def get_ai_client() -> AIServiceClient:
    return AIServiceClient()


def get_usage_client() -> UsageServiceClient:
    return UsageServiceClient()


def get_audit_repository(db: DbSession) -> AuditRepository:
    return AuditRepository(db)


def get_notification_repository(db: DbSession) -> NotificationRepository:
    return NotificationRepository(db)


def get_audit_service(
    repo: AuditRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(repo)


def get_dashboard_service(
    auth: AuthServiceClient = Depends(get_auth_client),
    user: UserServiceClient = Depends(get_user_client),
    usage: UsageServiceClient = Depends(get_usage_client),
) -> DashboardService:
    return DashboardService(
        auth_client=auth,
        user_client=user,
        usage_client=usage,
    )


def get_user_management_service(
    auth: AuthServiceClient = Depends(get_auth_client),
    user: UserServiceClient = Depends(get_user_client),
    ai: AIServiceClient = Depends(get_ai_client),
    usage: UsageServiceClient = Depends(get_usage_client),
    audit: AuditService = Depends(get_audit_service),
) -> UserManagementService:
    return UserManagementService(
        auth_client=auth,
        user_client=user,
        ai_client=ai,
        usage_client=usage,
        audit_service=audit,
    )


def get_analytics_service(
    ai: AIServiceClient = Depends(get_ai_client),
    usage: UsageServiceClient = Depends(get_usage_client),
    auth: AuthServiceClient = Depends(get_auth_client),
    user: UserServiceClient = Depends(get_user_client),
) -> AnalyticsService:
    return AnalyticsService(
        usage_client=usage,
        auth_client=auth,
        user_client=user,
        ai_client=ai,
    )


def get_system_health_service(
    auth: AuthServiceClient = Depends(get_auth_client),
    user: UserServiceClient = Depends(get_user_client),
    ai: AIServiceClient = Depends(get_ai_client),
    usage: UsageServiceClient = Depends(get_usage_client),
) -> SystemHealthService:
    return SystemHealthService(
        auth_client=auth,
        user_client=user,
        ai_client=ai,
        usage_client=usage,
    )


def get_notification_service(
    repo: NotificationRepository = Depends(get_notification_repository),
    auth: AuthServiceClient = Depends(get_auth_client),
    audit: AuditService = Depends(get_audit_service),
) -> NotificationService:
    return NotificationService(
        repository=repo,
        auth_client=auth,
        audit_service=audit,
    )
