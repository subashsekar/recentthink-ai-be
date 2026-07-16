"""Tests for Auth Service internal user-state endpoint and cache."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.enums import Role
from app.schemas.user_state import UserStateResponse
from app.services.user_state_cache import (
    clear_user_state_cache,
    get_cached_user_state,
    set_cached_user_state,
)
from app.services.user_state_service import UserStateService
from shared.config import get_settings
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER


@pytest.fixture(autouse=True)
def _clear_cache() -> Iterator[None]:
    clear_user_state_cache()
    yield
    clear_user_state_cache()


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def _headers() -> dict[str, str]:
    return {INTERNAL_SERVICE_TOKEN_HEADER: get_settings().internal_service_token}


def test_user_state_requires_internal_token(client: TestClient) -> None:
    response = client.get(f"/internal/auth/user-state/{uuid4()}")
    assert response.status_code == 401


def test_user_state_returns_snapshot(client: TestClient) -> None:
    from app.api.internal_auth import get_user_state_service
    from app.main import app

    user_id = uuid4()
    service = MagicMock(spec=UserStateService)
    service.get_user_state.return_value = UserStateResponse(
        user_id=user_id,
        is_active=True,
        is_blocked=False,
        role=Role.USER.value,
        pwd_ts=123.0,
    )
    app.dependency_overrides[get_user_state_service] = lambda: service
    try:
        response = client.get(
            f"/internal/auth/user-state/{user_id}",
            headers=_headers(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user_id)
    assert body["is_active"] is True
    assert body["is_blocked"] is False
    assert body["role"] == "USER"
    assert body["pwd_ts"] == 123.0


def test_user_state_service_caches_and_invalidates() -> None:
    user_id = uuid4()
    user = MagicMock()
    user.id = user_id
    user.is_active = True
    user.is_blocked = False
    user.role = Role.USER
    user.password_changed_at = datetime(2024, 1, 1, tzinfo=UTC)

    repo = MagicMock()
    repo.get_user_by_id.return_value = user
    service = UserStateService(user_repository=repo)

    first = service.get_user_state(user_id)
    second = service.get_user_state(user_id)
    assert first == second
    assert repo.get_user_by_id.call_count == 1
    assert get_cached_user_state(user_id) is not None

    UserStateService.invalidate(user_id)
    assert get_cached_user_state(user_id) is None

    user.is_blocked = True
    third = service.get_user_state(user_id)
    assert third.is_blocked is True
    assert repo.get_user_by_id.call_count == 2


def test_set_cached_user_state_roundtrip() -> None:
    user_id = uuid4()
    state = UserStateResponse(
        user_id=user_id,
        is_active=False,
        is_blocked=True,
        role="USER",
        pwd_ts=0.0,
    )
    set_cached_user_state(state)
    assert get_cached_user_state(user_id) == state
