"""Integration tests for User CRUD repository operations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from shared.exceptions import DuplicateEmailError, RecordNotFoundError

if TYPE_CHECKING:
    from app.repositories.user_repository import UserRepository

pytestmark = pytest.mark.db


@pytest.fixture
def user_payload() -> dict[str, str]:
    """Return unique user field values for a single test run."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "first_name": "Test",
        "last_name": "User",
        "email": f"user-crud-{suffix}@recentthink.test",
        "password_hash": "hashed-password-placeholder",
    }


def test_user_create_read(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """INSERT and READ: create a user and fetch by id and email."""
    from app.models.enums import Role

    created = user_repository.create_user(**user_payload)

    assert created.id is not None
    assert created.email == user_payload["email"]
    assert created.first_name == user_payload["first_name"]
    assert created.last_name == user_payload["last_name"]
    assert created.role is Role.USER
    assert created.is_verified is False
    assert created.is_active is True
    assert created.created_at is not None
    assert created.updated_at is not None

    by_id = user_repository.get_user_by_id(created.id)
    assert by_id is not None
    assert by_id.id == created.id

    by_email = user_repository.get_user_by_email(user_payload["email"])
    assert by_email is not None
    assert by_email.id == created.id


def test_user_role_default(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """Role defaults to USER when not explicitly provided."""
    from app.models.enums import Role

    created = user_repository.create_user(**user_payload)
    assert created.role is Role.USER


def test_user_update(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """UPDATE: modify an existing user record."""
    from app.models.enums import Role

    created = user_repository.create_user(**user_payload)

    updated = user_repository.update_user(
        created.id,
        first_name="Updated",
        is_verified=True,
        role=Role.ADMIN,
    )

    assert updated.first_name == "Updated"
    assert updated.is_verified is True
    assert updated.role is Role.ADMIN

    fetched = user_repository.get_user_by_id(created.id)
    assert fetched is not None
    assert fetched.first_name == "Updated"


def test_user_delete(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """DELETE: remove a user and confirm it no longer exists."""
    created = user_repository.create_user(**user_payload)
    user_id = created.id

    user_repository.delete_user(user_id)

    assert user_repository.get_user_by_id(user_id) is None


def test_user_list(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """READ: list users includes the newly created record."""
    created = user_repository.create_user(**user_payload)

    users, _total = user_repository.list_users()
    user_ids = {user.id for user in users}

    assert created.id in user_ids


def test_user_duplicate_email_raises(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """Error handling: duplicate email on create raises DuplicateEmailError."""
    user_repository.create_user(**user_payload)

    with pytest.raises(DuplicateEmailError):
        user_repository.create_user(**user_payload)


def test_user_update_missing_record_raises(
    user_repository: UserRepository,
) -> None:
    """Error handling: update on missing record raises RecordNotFoundError."""
    with pytest.raises(RecordNotFoundError):
        user_repository.update_user(uuid.uuid4(), first_name="Missing")


def test_user_delete_missing_record_raises(
    user_repository: UserRepository,
) -> None:
    """Error handling: delete on missing record raises RecordNotFoundError."""
    with pytest.raises(RecordNotFoundError):
        user_repository.delete_user(uuid.uuid4())


def test_user_update_rejects_non_editable_field(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """Whitelist: updating a non-editable field raises ValueError."""
    created = user_repository.create_user(**user_payload)

    with pytest.raises(ValueError):
        user_repository.update_user(created.id, id=uuid.uuid4())
