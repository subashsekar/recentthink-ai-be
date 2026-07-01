"""Integration tests for User CRUD repository operations."""

from __future__ import annotations

import uuid

import pytest

from app.repositories.user_repository import UserRepository
from shared.exceptions import DuplicateEmailError, RecordNotFoundError


@pytest.fixture
def user_payload() -> dict[str, str]:
    """Return unique user field values for a single test run."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "full_name": "Test User",
        "email": f"user-crud-{suffix}@recentthink.test",
        "password_hash": "hashed-password-placeholder",
    }


def test_user_create_read(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """INSERT and READ: create a user and fetch by id and email."""
    created = user_repository.create_user(**user_payload)

    assert created.id is not None
    assert created.email == user_payload["email"]
    assert created.full_name == user_payload["full_name"]
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


def test_user_update(
    user_repository: UserRepository,
    user_payload: dict[str, str],
) -> None:
    """UPDATE: modify an existing user record."""
    created = user_repository.create_user(**user_payload)

    updated = user_repository.update_user(
        created.id,
        full_name="Updated User",
        is_verified=True,
    )

    assert updated.full_name == "Updated User"
    assert updated.is_verified is True

    fetched = user_repository.get_user_by_id(created.id)
    assert fetched is not None
    assert fetched.full_name == "Updated User"


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

    users = user_repository.list_users()
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
        user_repository.update_user(uuid.uuid4(), full_name="Missing")


def test_user_delete_missing_record_raises(
    user_repository: UserRepository,
) -> None:
    """Error handling: delete on missing record raises RecordNotFoundError."""
    with pytest.raises(RecordNotFoundError):
        user_repository.delete_user(uuid.uuid4())
