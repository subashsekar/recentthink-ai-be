"""Profile repository unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from shared.exceptions import DuplicateUsernameError, RecordNotFoundError, RepositoryError
from shared.exceptions.base import BusinessException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


def test_create_profile_success() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    db = MagicMock()
    repo = ProfileRepository(db)
    user_id = uuid4()
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]

    profile = repo.create_profile(user_id=user_id, username="jane", first_name="Jane")

    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
    assert isinstance(profile, UserProfile)
    assert profile.user_id == user_id
    assert profile.username == "jane"


def test_create_profile_duplicate_user() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    existing = UserProfile(user_id=uuid4())
    repo.get_by_user_id = MagicMock(return_value=existing)  # type: ignore[method-assign]
    with pytest.raises(BusinessException):
        repo.create_profile(user_id=existing.user_id, username="x")


def test_create_profile_duplicate_username() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    user_id = uuid4()
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=UserProfile(user_id=uuid4()))  # type: ignore[method-assign]
    with pytest.raises(DuplicateUsernameError):
        repo.create_profile(user_id=user_id, username="taken")


def test_create_profile_integrity_error() -> None:
    from app.repositories.profile_repository import ProfileRepository

    db = MagicMock()
    repo = ProfileRepository(db)
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]
    db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))
    with pytest.raises(DuplicateUsernameError):
        repo.create_profile(user_id=uuid4(), username="jane")
    db.rollback.assert_called()


def test_update_profile_not_found() -> None:
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    with pytest.raises(RecordNotFoundError):
        repo.update_profile(uuid4(), first_name="A")


def test_update_profile_success() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    db = MagicMock()
    repo = ProfileRepository(db)
    user_id = uuid4()
    profile = UserProfile(user_id=user_id, first_name="Old")
    repo.get_by_user_id = MagicMock(return_value=profile)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=None)  # type: ignore[method-assign]
    updated = repo.update_profile(user_id, first_name="New", username="newuser")
    assert updated.first_name == "New"
    assert updated.username == "newuser"
    db.commit.assert_called_once()


def test_update_profile_username_taken() -> None:
    from app.models.profile import UserProfile
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    user_id = uuid4()
    profile = UserProfile(user_id=user_id)
    other = UserProfile(user_id=uuid4(), username="taken")
    repo.get_by_user_id = MagicMock(return_value=profile)  # type: ignore[method-assign]
    repo.get_by_username = MagicMock(return_value=other)  # type: ignore[method-assign]
    with pytest.raises(DuplicateUsernameError):
        repo.update_profile(user_id, username="taken")


def test_get_by_user_id_db_error() -> None:
    from app.repositories.profile_repository import ProfileRepository

    db = MagicMock()
    repo = ProfileRepository(db)
    db.scalar.side_effect = SQLAlchemyError("boom")
    with pytest.raises(RepositoryError):
        repo.get_by_user_id(uuid4())


def test_require_by_user_id() -> None:
    from app.repositories.profile_repository import ProfileRepository

    repo = ProfileRepository(MagicMock())
    repo.get_by_user_id = MagicMock(return_value=None)  # type: ignore[method-assign]
    with pytest.raises(RecordNotFoundError):
        repo.require_by_user_id(uuid4())
