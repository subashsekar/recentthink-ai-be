"""API tests for profile endpoints (auth overrides, no live DB)."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.exceptions import DuplicateUsernameError, RecordNotFoundError
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.base import ValidationException

TEST_USER_ID = uuid4()
OTHER_USER_ID = uuid4()


@pytest.fixture
def mock_user():
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(
        user_id=TEST_USER_ID,
        email="user@example.com",
        role="USER",
    )


@pytest.fixture
def mock_admin():
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(
        user_id=uuid4(),
        email="admin@example.com",
        role="ADMIN",
    )


@pytest.fixture
def mock_profile_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_statistics_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_avatar_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_public_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(
    mock_user,
    mock_profile_service: MagicMock,
    mock_statistics_service: MagicMock,
    mock_avatar_service: MagicMock,
    mock_public_service: MagicMock,
):
    from app.dependencies.auth import require_authenticated_user
    from app.dependencies.repositories import (
        get_avatar_service,
        get_profile_service,
        get_public_profile_service,
        get_statistics_service,
    )
    from app.main import app

    app.dependency_overrides[require_authenticated_user] = lambda: mock_user
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_statistics_service] = lambda: mock_statistics_service
    app.dependency_overrides[get_avatar_service] = lambda: mock_avatar_service
    app.dependency_overrides[get_public_profile_service] = lambda: mock_public_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _sample_profile(**overrides):
    from app.models.enums import CurrentStatus, PrimarySkill
    from app.models.profile import UserProfile

    now = datetime.now(tz=UTC)
    data = {
        "id": uuid4(),
        "user_id": TEST_USER_ID,
        "username": "jane",
        "first_name": "Jane",
        "last_name": "Doe",
        "mobile_number": "+15551234567",
        "profile_picture_url": None,
        "bio": "Hello",
        "current_status": CurrentStatus.STUDENT,
        "college": "MIT",
        "company": None,
        "current_role": None,
        "experience_years": 1.0,
        "primary_skill": PrimarySkill.PYTHON,
        "leetcode_username": "jane",
        "hackerrank_username": "jane",
        "github_username": "jane",
        "linkedin_url": "https://linkedin.com/in/jane",
        "portfolio_url": "https://jane.dev",
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    profile = UserProfile(
        **{k: v for k, v in data.items() if k not in {"id", "created_at", "updated_at"}}
    )
    profile.id = data["id"]
    profile.created_at = data["created_at"]
    profile.updated_at = data["updated_at"]
    return profile


def test_get_profile_requires_auth() -> None:
    from app.main import app

    with TestClient(app) as unauth:
        response = unauth.get("/profile")
    assert response.status_code in {401, 403}


def test_get_profile_success(client: TestClient, mock_profile_service: MagicMock) -> None:
    mock_profile_service.get_profile.return_value = _sample_profile()
    response = client.get("/profile", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "jane"
    assert body["mobile_number"] == "+15551234567"
    assert body["user_id"] == str(TEST_USER_ID)


def test_get_profile_not_found(client: TestClient, mock_profile_service: MagicMock) -> None:
    mock_profile_service.get_profile.side_effect = RecordNotFoundError("Profile not found.")
    response = client.get("/profile", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 404


def test_patch_profile_success(client: TestClient, mock_profile_service: MagicMock) -> None:
    mock_profile_service.update_profile.return_value = _sample_profile(bio="Updated")
    response = client.patch(
        "/profile",
        json={"bio": "Updated", "primary_skill": "Python"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    assert response.json()["bio"] == "Updated"


def test_patch_profile_duplicate_username(
    client: TestClient,
    mock_profile_service: MagicMock,
) -> None:
    mock_profile_service.update_profile.side_effect = DuplicateUsernameError(
        "Username is already taken.",
    )
    response = client.patch(
        "/profile",
        json={"username": "taken"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 409


def test_patch_profile_validation_error(client: TestClient) -> None:
    response = client.patch(
        "/profile",
        json={"portfolio_url": "not-a-url", "bio": "x" * 501},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 422


def test_get_statistics(client: TestClient, mock_statistics_service: MagicMock) -> None:
    from app.schemas.profile import StatisticsResponse

    mock_statistics_service.get_statistics.return_value = StatisticsResponse(
        problems_solved=10,
        courses_completed=2,
        patterns_learned=3,
        current_streak=4,
        longest_streak=8,
        learning_hours=12.5,
        last_active=None,
    )
    response = client.get("/profile/statistics", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 200
    assert response.json()["problems_solved"] == 10


def test_upload_avatar(client: TestClient, mock_avatar_service: MagicMock) -> None:
    from app.schemas.profile import AvatarUploadResponse

    mock_avatar_service.upload.return_value = AvatarUploadResponse(
        profile_picture_url="http://localhost:8002/media/avatars/x.jpg",
    )
    response = client.post(
        "/profile/avatar",
        files={"file": ("avatar.jpg", BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    assert "profile_picture_url" in response.json()


def test_upload_avatar_invalid(client: TestClient, mock_avatar_service: MagicMock) -> None:
    mock_avatar_service.upload.side_effect = ValidationException("Unsupported avatar format.")
    response = client.post(
        "/profile/avatar",
        files={"file": ("x.pdf", BytesIO(b"%PDF"), "application/pdf")},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 400


def test_delete_avatar(client: TestClient, mock_avatar_service: MagicMock) -> None:
    response = client.delete("/profile/avatar", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 204
    mock_avatar_service.delete.assert_called_once()


def test_public_profile(client: TestClient, mock_public_service: MagicMock) -> None:
    from app.models.enums import PrimarySkill
    from app.schemas.profile import PublicProfileResponse, StatisticsResponse

    mock_public_service.get_by_username.return_value = PublicProfileResponse(
        username="jane",
        first_name="Jane",
        last_name="Doe",
        bio="Hi",
        github_username="jane",
        linkedin_url="https://linkedin.com/in/jane",
        portfolio_url="https://jane.dev",
        primary_skill=PrimarySkill.PYTHON,
        profile_picture_url=None,
        statistics=StatisticsResponse(),
    )
    response = client.get("/profile/public/jane")
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "jane"
    assert "mobile_number" not in body
    assert "email" not in body
    assert "user_id" not in body
    assert "statistics" in body


def test_public_profile_not_found(client: TestClient, mock_public_service: MagicMock) -> None:
    mock_public_service.get_by_username.side_effect = RecordNotFoundError("Profile not found.")
    response = client.get("/profile/public/missing")
    assert response.status_code == 404


def test_admin_can_read_other_profile(
    mock_admin,
    mock_profile_service: MagicMock,
    mock_statistics_service: MagicMock,
    mock_avatar_service: MagicMock,
    mock_public_service: MagicMock,
) -> None:
    from app.dependencies.auth import require_authenticated_user
    from app.dependencies.repositories import (
        get_avatar_service,
        get_profile_service,
        get_public_profile_service,
        get_statistics_service,
    )
    from app.main import app

    app.dependency_overrides[require_authenticated_user] = lambda: mock_admin
    app.dependency_overrides[get_profile_service] = lambda: mock_profile_service
    app.dependency_overrides[get_statistics_service] = lambda: mock_statistics_service
    app.dependency_overrides[get_avatar_service] = lambda: mock_avatar_service
    app.dependency_overrides[get_public_profile_service] = lambda: mock_public_service
    mock_profile_service.get_profile.return_value = _sample_profile(user_id=OTHER_USER_ID)
    try:
        with TestClient(app) as admin_client:
            response = admin_client.get(
                f"/profile?user_id={OTHER_USER_ID}",
                headers={"Authorization": "Bearer fake"},
            )
        assert response.status_code == 200
        mock_profile_service.get_profile.assert_called_once()
        kwargs = mock_profile_service.get_profile.call_args.kwargs
        assert kwargs["target_user_id"] == OTHER_USER_ID
        assert kwargs["actor_role"] == "ADMIN"
    finally:
        app.dependency_overrides.clear()


def test_user_forbidden_reading_other_profile(
    client: TestClient,
    mock_profile_service: MagicMock,
) -> None:
    mock_profile_service.get_profile.side_effect = ForbiddenError(
        "You do not have permission to view this profile.",
    )
    response = client.get(
        f"/profile?user_id={OTHER_USER_ID}",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


def test_health_still_works(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_get_profile_completion(client: TestClient, mock_profile_service: MagicMock) -> None:
    from app.schemas.profile import ProfileCompletionResponse

    mock_profile_service.get_profile_completion.return_value = ProfileCompletionResponse(
        percent=58,
        completed_fields=["username", "first_name"],
        missing_fields=["bio"],
        is_complete=False,
    )
    response = client.get("/profile/completion", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 200
    body = response.json()
    assert body["percent"] == 58
    assert body["is_complete"] is False


def test_search_public_profiles(client: TestClient, mock_public_service: MagicMock) -> None:
    from app.models.enums import PrimarySkill
    from app.schemas.profile import PublicProfileListItem, PublicProfileSearchResponse

    mock_public_service.search.return_value = PublicProfileSearchResponse(
        items=[
            PublicProfileListItem(
                username="jane",
                first_name="Jane",
                last_name="Doe",
                primary_skill=PrimarySkill.PYTHON,
                profile_picture_url=None,
                bio="Hi",
            )
        ],
        page=1,
        page_size=20,
        total=1,
    )
    response = client.get("/profile/search?q=jane&page=1&page_size=20")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "jane"
    assert "statistics" not in body["items"][0]
