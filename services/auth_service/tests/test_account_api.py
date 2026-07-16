"""API tests for /account disable, delete, and status."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.exceptions.auth import InvalidCredentialsError
from shared.exceptions.base import BusinessException


@pytest.fixture
def active_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.email = "jane@example.com"
    user.is_active = True
    user.disabled_at = None
    user.role = "USER"
    return user


@pytest.fixture
def account_service_mock() -> MagicMock:
    from app.services.account_service import AccountService

    return MagicMock(spec=AccountService)


@pytest.fixture
def client_with_account_mock(
    active_user: MagicMock,
    account_service_mock: MagicMock,
) -> Iterator[TestClient]:
    from app.dependencies.auth import get_account_service, require_user
    from app.main import app

    app.dependency_overrides[require_user] = lambda: active_user
    app.dependency_overrides[get_account_service] = lambda: account_service_mock
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_status(client_with_account_mock: TestClient, account_service_mock: MagicMock) -> None:
    from app.schemas.account import AccountStatusResponse

    account_service_mock.get_status.return_value = AccountStatusResponse(
        is_active=True,
        is_blocked=False,
        disabled_at=None,
        blocked_at=None,
    )
    response = client_with_account_mock.get(
        "/account/status",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "is_active": True,
        "is_blocked": False,
        "disabled_at": None,
        "blocked_at": None,
    }


def test_disable_success(
    client_with_account_mock: TestClient,
    account_service_mock: MagicMock,
) -> None:
    from app.schemas.account import DisableAccountResponse

    disabled_at = datetime.now(tz=UTC)
    account_service_mock.disable_account.return_value = DisableAccountResponse(
        is_active=False,
        disabled_at=disabled_at,
    )
    response = client_with_account_mock.patch(
        "/account/disable",
        json={"password": "ValidP@ss1"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["message"] == "Account disabled successfully."


def test_disable_wrong_password(
    client_with_account_mock: TestClient,
    account_service_mock: MagicMock,
) -> None:
    account_service_mock.disable_account.side_effect = InvalidCredentialsError(
        "Current password is incorrect.",
    )
    response = client_with_account_mock.patch(
        "/account/disable",
        json={"password": "wrong"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 401


def test_disable_already_disabled(
    client_with_account_mock: TestClient,
    account_service_mock: MagicMock,
) -> None:
    account_service_mock.disable_account.side_effect = BusinessException(
        "Account is already disabled.",
    )
    response = client_with_account_mock.patch(
        "/account/disable",
        json={"password": "ValidP@ss1"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 400


def test_delete_success(
    client_with_account_mock: TestClient,
    account_service_mock: MagicMock,
) -> None:
    account_service_mock.delete_account.return_value = None
    response = client_with_account_mock.request(
        "DELETE",
        "/account",
        json={"password": "ValidP@ss1", "confirm": True},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 204


def test_delete_without_confirm(
    client_with_account_mock: TestClient,
    account_service_mock: MagicMock,
) -> None:
    account_service_mock.delete_account.side_effect = BusinessException(
        "Account deletion requires confirm=true.",
    )
    response = client_with_account_mock.request(
        "DELETE",
        "/account",
        json={"password": "ValidP@ss1", "confirm": False},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 400


def test_account_requires_auth() -> None:
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/account/status").status_code in {401, 403}
        assert client.patch("/account/disable", json={"password": "x"}).status_code in {
            401,
            403,
        }
