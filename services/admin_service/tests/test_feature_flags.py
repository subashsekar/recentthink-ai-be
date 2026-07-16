"""Feature flag API tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import AuthenticatedUser, require_admin_user
from app.dependencies.services import get_feature_flag_service
from app.main import app
from app.schemas.admin import (
    FeatureFlagListResponse,
    FeatureFlagResponse,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_feature_flags_require_admin(client: TestClient) -> None:
    response = client.get("/admin/feature-flags")
    assert response.status_code in {401, 403}


def test_feature_flags_crud(client: TestClient) -> None:
    admin_id = uuid4()
    flag_id = uuid4()
    now = datetime.now(tz=UTC)

    def _admin() -> AuthenticatedUser:
        return AuthenticatedUser(
            user_id=admin_id,
            email="admin@example.com",
            role="ADMIN",
        )

    class _Svc:
        def list(self, *, page=1, page_size=50) -> FeatureFlagListResponse:
            return FeatureFlagListResponse(
                items=[
                    FeatureFlagResponse(
                        id=flag_id,
                        key="chat_v2",
                        name="Chat V2",
                        description="Enable chat v2",
                        enabled=True,
                        created_at=now,
                        updated_at=now,
                    )
                ],
                total=1,
                page=page,
                page_size=page_size,
            )

        def get_by_key(self, key: str) -> FeatureFlagResponse:
            return FeatureFlagResponse(
                id=flag_id,
                key=key,
                name="Chat V2",
                description="Enable chat v2",
                enabled=True,
                created_at=now,
                updated_at=now,
            )

        def create(self, payload, *, actor_id) -> FeatureFlagResponse:
            return FeatureFlagResponse(
                id=flag_id,
                key=payload.key,
                name=payload.name,
                description=payload.description,
                enabled=payload.enabled,
                created_at=now,
                updated_at=now,
            )

        def update(self, key, payload, *, actor_id) -> FeatureFlagResponse:
            return FeatureFlagResponse(
                id=flag_id,
                key=key,
                name=payload.name or "Chat V2",
                description=payload.description,
                enabled=payload.enabled if payload.enabled is not None else True,
                created_at=now,
                updated_at=now,
            )

        def delete(self, key, *, actor_id) -> None:
            return None

    app.dependency_overrides[require_admin_user] = _admin
    app.dependency_overrides[get_feature_flag_service] = lambda: _Svc()
    try:
        listed = client.get("/admin/feature-flags")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["key"] == "chat_v2"

        fetched = client.get("/admin/feature-flags/chat_v2")
        assert fetched.status_code == 200
        assert fetched.json()["enabled"] is True

        created = client.post(
            "/admin/feature-flags",
            json={
                "key": "new_flag",
                "name": "New Flag",
                "description": "Test",
                "enabled": False,
            },
        )
        assert created.status_code == 201
        assert created.json()["key"] == "new_flag"

        updated = client.patch(
            "/admin/feature-flags/chat_v2",
            json={"enabled": False},
        )
        assert updated.status_code == 200
        assert updated.json()["key"] == "chat_v2"

        deleted = client.delete("/admin/feature-flags/chat_v2")
        assert deleted.status_code == 204
    finally:
        app.dependency_overrides.clear()
