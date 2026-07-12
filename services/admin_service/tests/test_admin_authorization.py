"""Authorization and audit tests for Admin Service."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, require_admin_user
from app.dependencies.services import get_dashboard_service
from app.main import app
from app.models.enums import AuditAction
from app.schemas.admin import DashboardResponse
from app.services.audit_service import AuditService


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_dashboard_requires_auth(client: TestClient) -> None:
    response = client.get("/admin/dashboard")
    assert response.status_code in {401, 403}


def test_dashboard_rejects_non_admin(client: TestClient) -> None:
    from shared.exceptions.auth import ForbiddenError

    def _forbid() -> AuthenticatedUser:
        raise ForbiddenError("Admin privileges required.")

    app.dependency_overrides[require_admin_user] = _forbid
    try:
        response = client.get("/admin/dashboard")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_dashboard_allows_admin(client: TestClient) -> None:
    admin_id = uuid4()

    def _admin() -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=admin_id,
            email="admin@example.com",
            role="ADMIN",
        )

    class _DashSvc:
        async def get_dashboard(self) -> DashboardResponse:
            return DashboardResponse(total_users=3, active_users=2, blocked_users=1)

    app.dependency_overrides[require_admin_user] = _admin
    app.dependency_overrides[get_dashboard_service] = lambda: _DashSvc()
    try:
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        body = response.json()
        assert body["total_users"] == 3
        assert body["blocked_users"] == 1
    finally:
        app.dependency_overrides.clear()


def test_audit_service_logs_action() -> None:
    repo = MagicMock()
    row = MagicMock()
    row.id = uuid4()
    row.admin_id = uuid4()
    row.action = AuditAction.USER_BLOCKED.value
    row.target_user_id = uuid4()
    row.reason = "spam"
    row.created_at = MagicMock()
    repo.create.return_value = row
    repo.list_logs.return_value = ([row], 1)

    service = AuditService(repo)
    created = service.log(
        admin_id=row.admin_id,
        action=AuditAction.USER_BLOCKED.value,
        target_user_id=row.target_user_id,
        reason="spam",
    )
    assert created.action == AuditAction.USER_BLOCKED.value
    repo.create.assert_called_once()

    listed = service.list_logs(page=1, page_size=10)
    assert listed.total == 1
    assert listed.items[0].action == AuditAction.USER_BLOCKED.value
