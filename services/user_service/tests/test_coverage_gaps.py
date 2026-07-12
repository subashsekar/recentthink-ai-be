"""Extra coverage for remaining service / repository branches."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from shared.exceptions import RepositoryError
from shared.exceptions.base import ValidationException
from shared.storage.base import StorageError
from sqlalchemy.exc import SQLAlchemyError


def test_profile_service_create_profile() -> None:
    from app.models.profile import UserProfile
    from app.schemas.profile import ProfileCreate
    from app.services.profile_service import ProfileService

    user_id = uuid4()
    created = UserProfile(user_id=user_id, username="jane")
    service = ProfileService(MagicMock())
    with patch.object(service._profiles, "create_profile", return_value=created) as create:
        result = service.create_profile(
            user_id=user_id,
            payload=ProfileCreate(username="jane", first_name="Jane"),
        )
    create.assert_called_once()
    assert result.username == "jane"


def test_profile_service_admin_write_forbidden_path() -> None:
    from app.services.profile_service import ProfileService
    from shared.exceptions.auth import ForbiddenError

    service = ProfileService(MagicMock())
    with pytest.raises(ForbiddenError):
        service._assert_can_write(
            actor_id=uuid4(),
            actor_role="USER",
            target_user_id=uuid4(),
        )


def test_public_profile_invalid_username() -> None:
    from app.services.public_profile_service import PublicProfileService

    service = PublicProfileService(MagicMock())
    with pytest.raises(ValidationException):
        service.get_by_username("ab")


def test_avatar_empty_and_oversized() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    user_id = uuid4()
    service = AvatarService(MagicMock(), storage=MagicMock())
    settings = MagicMock()
    settings.avatar_allowed_content_types = ["image/png"]
    settings.avatar_max_bytes = 10
    service._settings = settings

    with patch.object(
        service._profiles,
        "require_by_user_id",
        return_value=UserProfile(user_id=user_id),
    ):
        with pytest.raises(ValidationException, match="empty"):
            service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"",
                content_type="image/png",
            )
        with pytest.raises(ValidationException, match="maximum size"):
            service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"x" * 20,
                content_type="image/png",
            )


def test_avatar_storage_error() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    user_id = uuid4()
    storage = MagicMock()
    storage.save.side_effect = StorageError("fail")
    service = AvatarService(MagicMock(), storage=storage)
    settings = MagicMock()
    settings.avatar_allowed_content_types = ["image/png"]
    settings.avatar_max_bytes = 1024
    service._settings = settings
    with patch.object(
        service._profiles,
        "require_by_user_id",
        return_value=UserProfile(user_id=user_id),
    ):
        with pytest.raises(ValidationException, match="Failed to store"):
            service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"abc",
                content_type="image/png",
            )


def test_avatar_delete_noop_and_foreign_url() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    user_id = uuid4()
    profile = UserProfile(user_id=user_id, profile_picture_url=None)
    service = AvatarService(MagicMock(), storage=MagicMock())
    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        service.delete(actor_id=user_id, actor_role="USER", target_user_id=user_id)

    service._settings = MagicMock(storage_public_base_url="http://localhost:8002/media")
    service._safe_delete_url("https://cdn.example.com/a.jpg")
    service._storage.delete.side_effect = StorageError("x")
    service._safe_delete_url("http://localhost:8002/media/avatars/a.jpg")


def test_avatar_admin_can_upload() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    owner = uuid4()
    admin = uuid4()
    storage = MagicMock()
    storage.save.return_value = "http://localhost:8002/media/avatars/a.png"
    service = AvatarService(MagicMock(), storage=storage)
    settings = MagicMock()
    settings.avatar_allowed_content_types = ["image/png"]
    settings.avatar_max_bytes = 1024
    settings.storage_public_base_url = "http://localhost:8002/media"
    service._settings = settings
    profile = UserProfile(user_id=owner)
    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        with patch.object(service._profiles, "update_profile", return_value=profile):
            result = service.upload(
                actor_id=admin,
                actor_role="ADMIN",
                target_user_id=owner,
                data=b"abc",
                content_type="image/png",
            )
    assert result.profile_picture_url.endswith(".png")


def test_repository_error_paths() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository
    from app.repositories.statistics_repository import StatisticsRepository

    db = MagicMock()
    repo = ProfileRepository(db)
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]
    db.commit.side_effect = SQLAlchemyError("boom")
    with pytest.raises(RepositoryError):
        repo.create_profile(user_id=uuid4(), username="jane")

    db2 = MagicMock()
    repo2 = ProfileRepository(db2)
    profile = UserProfile(user_id=uuid4())
    repo2.get_by_user_id = MagicMock(return_value=profile)  # type: ignore[method-assign]
    repo2.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]
    db2.commit.side_effect = SQLAlchemyError("boom")
    with pytest.raises(RepositoryError):
        repo2.update_profile(profile.user_id, first_name="X")

    with pytest.raises(ValueError):
        repo2.update_profile(profile.user_id, not_a_field="x")

    db3 = MagicMock()
    db3.scalar.side_effect = SQLAlchemyError("boom")
    repo3 = ProfileRepository(db3)
    with pytest.raises(RepositoryError):
        repo3.get_by_username("jane")
    with pytest.raises(RepositoryError):
        repo3.get_by_id(uuid4())

    db4 = MagicMock()
    db4.execute.side_effect = SQLAlchemyError("boom")
    with pytest.raises(RepositoryError):
        StatisticsRepository(db4).get_for_user(uuid4())


def test_schema_validation_errors() -> None:
    from app.schemas.profile import ProfileCreate, ProfileUpdate
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ProfileCreate(username="ab")
    with pytest.raises(ValidationError):
        ProfileUpdate(mobile_number="12")
    with pytest.raises(ValidationError):
        ProfileUpdate(linkedin_url="https://example.com/x")
    with pytest.raises(ValidationError):
        ProfileCreate(portfolio_url="ftp://x.com")
    with pytest.raises(ValidationError):
        ProfileUpdate(github_username="!!!")
    with pytest.raises(ValidationError):
        ProfileCreate(bio="x" * 501)
    with pytest.raises(ValidationError):
        ProfileUpdate(first_name="x" * 200)


def test_dependency_providers() -> None:
    from app.dependencies.repositories import (
        get_avatar_service,
        get_profile_service,
        get_public_profile_service,
        get_statistics_service,
    )

    db = MagicMock()
    assert get_profile_service(db) is not None
    assert get_statistics_service(db) is not None
    assert get_avatar_service(db) is not None
    assert get_public_profile_service(db) is not None


def test_database_exports() -> None:
    from app.database import Base, SessionLocal, engine, get_db

    assert Base is not None
    assert SessionLocal is not None
    assert engine is not None
    assert callable(get_db)


def test_auth_incomplete_payload() -> None:
    from app.dependencies.auth import AuthenticatedUser, get_current_user, require_authenticated_user
    from shared.exceptions.auth import InvalidTokenError
    from shared.security.jwt import TokenType

    credentials = MagicMock()
    credentials.credentials = "t"
    with patch(
        "app.dependencies.auth.verify_token",
        return_value={"token_type": TokenType.ACCESS.value},
    ):
        with pytest.raises(InvalidTokenError):
            get_current_user(credentials)

    user = AuthenticatedUser(user_id=uuid4(), email="a@b.com", role="USER")
    assert require_authenticated_user(user) is user


def test_require_by_user_id_success() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    profile = UserProfile(user_id=uuid4())
    repo.get_by_user_id = MagicMock(return_value=profile)  # type: ignore[method-assign]
    assert repo.require_by_user_id(profile.user_id) is profile


def test_update_profile_integrity_error() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository
    from shared.exceptions import DuplicateUsernameError
    from sqlalchemy.exc import IntegrityError

    db = MagicMock()
    repo = ProfileRepository(db)
    profile = UserProfile(user_id=uuid4())
    repo.get_by_user_id = MagicMock(return_value=profile)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]
    db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))
    with pytest.raises(DuplicateUsernameError):
        repo.update_profile(profile.user_id, username="taken")


def test_public_profile_blank_username() -> None:
    from app.services.public_profile_service import PublicProfileService

    service = PublicProfileService(MagicMock())
    with pytest.raises(ValidationException):
        service.get_by_username("   ")


def test_avatar_extension_fallback_and_replace() -> None:
    from app.models.profile import UserProfile
    from app.services.avatar_service import AvatarService

    user_id = uuid4()
    storage = MagicMock()
    storage.save.return_value = "http://localhost:8002/media/avatars/new.bin"
    service = AvatarService(MagicMock(), storage=storage)
    settings = MagicMock()
    settings.avatar_allowed_content_types = ["image/jpeg"]
    settings.avatar_max_bytes = 1024
    settings.storage_public_base_url = "http://localhost:8002/media"
    service._settings = settings
    profile = UserProfile(
        user_id=user_id,
        profile_picture_url="http://localhost:8002/media/avatars/old.jpg",
    )

    def _update(_uid, **fields):
        for key, value in fields.items():
            setattr(profile, key, value)
        return profile

    with patch.object(service._profiles, "require_by_user_id", return_value=profile):
        with patch.object(service._profiles, "update_profile", side_effect=_update):
            # unknown content-type mapping uses filename suffix / .bin
            service._settings.avatar_allowed_content_types = ["application/octet-stream"]
            # force allowed type that isn't in EXT map
            result = service.upload(
                actor_id=user_id,
                actor_role="USER",
                target_user_id=user_id,
                data=b"abc",
                content_type="application/octet-stream",
                filename=None,
            )
    assert result.profile_picture_url.endswith(".bin")
    storage.delete.assert_called()
