"""Integration tests for Admin CRUD repository operations."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

import pytest

from shared.exceptions import DuplicateEmailError, RecordNotFoundError

if TYPE_CHECKING:
    from app.repositories.admin_repository import AdminRepository

pytestmark = pytest.mark.db


@pytest.fixture
def admin_payload() -> dict[str, str]:
    """Return unique admin field values for a single test run."""
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"admin-crud-{suffix}@recentthink.test",
        "password_hash": "hashed-password-placeholder",
        "first_name": "Test",
        "last_name": "Admin",
    }


def test_admin_create_read(
    admin_repository: AdminRepository,
    admin_payload: dict[str, str],
) -> None:
    """INSERT and READ: create an admin and fetch by id and email."""
    created = admin_repository.create_admin(**admin_payload)

    assert created.id is not None
    assert created.email == admin_payload["email"]
    assert created.first_name == admin_payload["first_name"]
    assert created.created_at is not None
    assert created.updated_at is not None

    by_id = admin_repository.get_admin_by_id(created.id)
    assert by_id is not None
    assert by_id.id == created.id

    by_email = admin_repository.get_admin_by_email(admin_payload["email"])
    assert by_email is not None
    assert by_email.id == created.id


def test_admin_update(
    admin_repository: AdminRepository,
    admin_payload: dict[str, str],
) -> None:
    """UPDATE: modify an existing admin record."""
    created = admin_repository.create_admin(**admin_payload)

    updated = admin_repository.update_admin(
        created.id,
        first_name="Updated",
        last_name="Name",
    )

    assert updated.first_name == "Updated"
    assert updated.last_name == "Name"

    fetched = admin_repository.get_admin_by_id(created.id)
    assert fetched is not None
    assert fetched.first_name == "Updated"


def test_admin_delete(
    admin_repository: AdminRepository,
    admin_payload: dict[str, str],
) -> None:
    """DELETE: remove an admin and confirm it no longer exists."""
    created = admin_repository.create_admin(**admin_payload)
    admin_id = created.id

    admin_repository.delete_admin(admin_id)

    assert admin_repository.get_admin_by_id(admin_id) is None


def test_admin_list(
    admin_repository: AdminRepository,
    admin_payload: dict[str, str],
) -> None:
    """READ: list admins includes the newly created record."""
    created = admin_repository.create_admin(**admin_payload)

    admins = admin_repository.list_admins()
    admin_ids = {admin.id for admin in admins}

    assert created.id in admin_ids


def test_admin_duplicate_email_raises(
    admin_repository: AdminRepository,
    admin_payload: dict[str, str],
) -> None:
    """Error handling: duplicate email on create raises DuplicateEmailError."""
    admin_repository.create_admin(**admin_payload)

    with pytest.raises(DuplicateEmailError):
        admin_repository.create_admin(**admin_payload)


def test_admin_update_missing_record_raises(
    admin_repository: AdminRepository,
) -> None:
    """Error handling: update on missing record raises RecordNotFoundError."""
    with pytest.raises(RecordNotFoundError):
        admin_repository.update_admin(uuid.uuid4(), first_name="Missing")


def test_admin_delete_missing_record_raises(
    admin_repository: AdminRepository,
) -> None:
    """Error handling: delete on missing record raises RecordNotFoundError."""
    with pytest.raises(RecordNotFoundError):
        admin_repository.delete_admin(uuid.uuid4())
