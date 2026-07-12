"""Profile / statistics / avatar / public profile service tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from shared.exceptions import RecordNotFoundError
from shared.exceptions.auth import ForbiddenError
from shared.exceptions.base import ValidationException


def test_profile_service_owner_get_and_update() -> None:
    from app.models.profile import UserProfile
    from app.schemas.profile import ProfileUpdate
    from app.services.profile_service import ProfileService

    db = MagicMock()
    user_id = uuid4()
    profile = UserProfile(user_id=user_id, first_name="Jane")
    service = ProfileService(db)
    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        got = service.get_profile(actor_id=user_id, actor_role="USER", target_user_id=user_id)
        assert got.first_name == "Jane"

    with patch.object(service._profiles, "get_by_user_id", return_value=profile):
        with patch.object(service._profiles, "update_profile", return_value=profile) as upd:
            service.update_profile(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                payload=ProfileUpdate(bio="hi"),
            )
            upd.assert_called_once()


def test_profile_service_forbidden_for_other_user() -> None:
    from app.services.profile_service import ProfileService

    service = ProfileService(MagicMock())
    with pytest.raises(ForbiddenError):
        service.get_profile(
            actor_id=uuid4(),
            actor_role="USER",
            target_user_id=uuid4(),
        )


def test_profile_service_admin_can_read_any() -> None:
    from app.models.profile import UserProfile
    from app.services.profile_service import ProfileService

    db = MagicMock()
    target = uuid4()
    profile = UserProfile(user_id=target)
    service = ProfileService(db)
    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        got = service.get_profile(
            actor_id=uuid4(),
            actor_role="ADMIN",
            target_user_id=target,
        )
    assert got.user_id == target


def test_profile_service_creates_on_first_update() -> None:
    from app.models.profile import UserProfile
    from app.schemas.profile import ProfileUpdate
    from app.services.profile_service import ProfileService

    db = MagicMock()
    user_id = uuid4()
    created = UserProfile(user_id=user_id, username="jane")
    service = ProfileService(db)
    with patch.object(service._profiles, "get_by_user_id", return_value=None):
        with patch.object(service, "create_profile", return_value=created) as create:
            result = service.update_profile(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                payload=ProfileUpdate(username="jane", first_name="Jane"),
            )
            create.assert_called_once()
            assert result.username == "jane"


def test_statistics_service_owner() -> None:
    from app.repositories.statistics_repository import UserStatistics
    from app.services.statistics_service import StatisticsService

    db = MagicMock()
    user_id = uuid4()
    service = StatisticsService(db)
    raw = UserStatistics(
        problems_solved=5,
        courses_completed=1,
        patterns_learned=2,
        current_streak=3,
        longest_streak=4,
        learning_hours=1.5,
        last_active=datetime.now(tz=UTC),
    )
    with patch.object(service._profiles, "require_by_user_id", return_value=MagicMock()):
        with patch.object(service._stats, "get_for_user", return_value=raw):
            resp = service.get_statistics(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
            )
    assert resp.problems_solved == 5


def test_statistics_service_forbidden() -> None:
    from app.services.statistics_service import StatisticsService

    service = StatisticsService(MagicMock())
    with pytest.raises(ForbiddenError):
        service.get_statistics(
            actor_id=uuid4(),
            actor_role="USER",
            target_user_id=uuid4(),
        )


def test_public_profile_service() -> None:
    from app.models.enums import PrimarySkill
    from app.models.profile import UserProfile
    from app.repositories.statistics_repository import UserStatistics
    from app.services.public_profile_service import PublicProfileService

    db = MagicMock()
    user_id = uuid4()
    profile = UserProfile(
        user_id=user_id,
        username="jane",
        first_name="Jane",
        last_name="Doe",
        bio="Builder",
        github_username="jane",
        primary_skill=PrimarySkill.PYTHON,
    )
    service = PublicProfileService(db)
    with patch.object(service._profiles, "get_by_username", return_value=profile):
        with patch.object(
            service._stats,
            "get_for_user",
            return_value=UserStatistics(0, 0, 0, 0, 0, 0.0, None),
        ):
            public = service.get_by_username("Jane")
    assert public.username == "jane"
    assert public.first_name == "Jane"
    assert "mobile_number" not in public.model_dump()
    assert "email" not in public.model_dump()
    assert "user_id" not in public.model_dump()


def test_public_profile_not_found() -> None:
    from app.services.public_profile_service import PublicProfileService

    service = PublicProfileService(MagicMock())
    with patch.object(service._profiles, "get_by_username", return_value=None):
        with pytest.raises(RecordNotFoundError):
            service.get_by_username("missing")


def test_avatar_upload_and_delete(tmp_path) -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService
    from shared.storage.local import LocalStorageBackend

    db = MagicMock()
    user_id = uuid4()
    profile = UserProfile(user_id=user_id)
    storage = LocalStorageBackend(
        root_dir=tmp_path,
        public_base_url="http://localhost:8002/media",
    )
    service = AvatarService(db, storage=storage)

    def _update(_uid, **fields):
        for key, value in fields.items():
            setattr(profile, key, value)
        return profile

    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        with patch.object(service._profiles, "update_profile", side_effect=_update):
            settings = MagicMock()
            settings.avatar_allowed_content_types = ["image/jpeg", "image/png"]
            settings.avatar_max_bytes = 1024
            settings.storage_public_base_url = "http://localhost:8002/media"
            service._settings = settings
            result = service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"\xff\xd8\xff",
                content_type="image/jpeg",
                filename="a.jpg",
            )
    assert result.profile_picture_url.startswith("http://localhost:8002/media/avatars/")

    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        with patch.object(service._profiles, "update_profile", side_effect=_update):
            service._settings = MagicMock(storage_public_base_url="http://localhost:8002/media")
            service.delete(actor_id=user_id, actor_role="USER", target_user_id=user_id)


def test_avatar_rejects_bad_type() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    user_id = uuid4()
    service = AvatarService(MagicMock(), storage=MagicMock())
    with patch.object(
        service._profiles,
        "require_by_user_id",
        return_value=UserProfile(user_id=user_id),
    ):
        settings = MagicMock()
        settings.avatar_allowed_content_types = ["image/png"]
        settings.avatar_max_bytes = 1024
        service._settings = settings
        with pytest.raises(ValidationException):
            service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"abc",
                content_type="application/pdf",
            )


def test_avatar_forbidden_for_other_user() -> None:
    from app.services.avatar_service import AvatarService

    service = AvatarService(MagicMock(), storage=MagicMock())
    with pytest.raises(ForbiddenError):
        service.upload(
            actor_id=uuid4(),
            actor_role="USER",
            target_user_id=uuid4(),
            data=b"x",
            content_type="image/png",
        )


def test_profile_create_schema_normalizes() -> None:
    from app.schemas.profile import ProfileCreate

    payload = ProfileCreate(
        username="  Jane_Dev ",
        github_username="@Octo",
        bio="  hello ",
        mobile_number="+15551234567",
        linkedin_url="https://linkedin.com/in/jane",
        portfolio_url="https://jane.dev",
    )
    assert payload.username == "jane_dev"
    assert payload.github_username == "octo"
    assert payload.bio == "hello"
