"""Notification API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, require_authenticated_user
from app.dependencies.services import get_notification_service
from app.main import app
from app.schemas.admin import (
    MarkAllReadResponse,
    NotificationItem,
    NotificationListResponse,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_list_notifications(client: TestClient) -> None:
    user_id = uuid4()
    nid = uuid4()

    def _user() -> AuthenticatedUser:
        return AuthenticatedUser(user_id=user_id, email="u@example.com", role="USER")

    class _Svc:
        def list_for_user(self, *args, **kwargs) -> NotificationListResponse:
            return NotificationListResponse(
                items=[
                    NotificationItem(
                        id=nid,
                        user_id=user_id,
                        title="Hello",
                        message="World",
                        type="info",
                        is_read=False,
                        created_at=datetime.now(tz=UTC),
                    )
                ],
                total=1,
                page=1,
                page_size=50,
            )

        def mark_read(self, notification_id, uid) -> NotificationItem:
            return NotificationItem(
                id=notification_id,
                user_id=uid,
                title="Hello",
                message="World",
                type="info",
                is_read=True,
                created_at=datetime.now(tz=UTC),
            )

        def mark_all_read(self, uid) -> MarkAllReadResponse:
            return MarkAllReadResponse(message="ok", updated=2)

    app.dependency_overrides[require_authenticated_user] = _user
    app.dependency_overrides[get_notification_service] = lambda: _Svc()
    try:
        listed = client.get("/notifications")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1

        read_one = client.patch(f"/notifications/{nid}/read")
        assert read_one.status_code == 200
        assert read_one.json()["is_read"] is True

        read_all = client.patch("/notifications/read-all")
        assert read_all.status_code == 200
        assert read_all.json()["updated"] == 2
    finally:
        app.dependency_overrides.clear()
