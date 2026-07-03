"""Unit tests for super-admin seeding."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.models.enums import Role
from app.services.super_admin_seed_service import seed_super_admin
from shared.config import Settings


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock()


@pytest.fixture
def db_session() -> MagicMock:
    return MagicMock()


@pytest.fixture
def seed_settings() -> Settings:
    return Settings(
        secret_key="x" * 32,
        super_admin_email="super@example.com",
        super_admin_password="SuperAdmin1!",
        super_admin_first_name="Super",
        super_admin_last_name="Admin",
    )


def test_seed_creates_super_admin_when_none_exists(
    db_session: MagicMock,
    user_repository: MagicMock,
    seed_settings: Settings,
) -> None:
    user_repository.exists_user_with_role.return_value = False

    created = seed_super_admin(
        db_session,
        settings=seed_settings,
        user_repository=user_repository,
    )

    assert created is True
    user_repository.create_user.assert_called_once()
    kwargs = user_repository.create_user.call_args.kwargs
    assert kwargs["email"] == "super@example.com"
    assert kwargs["role"] is Role.SUPER_ADMIN
    assert kwargs["is_verified"] is True
    assert kwargs["is_active"] is True
    assert kwargs["password_hash"] != "SuperAdmin1!"


def test_seed_skips_when_super_admin_exists(
    db_session: MagicMock,
    user_repository: MagicMock,
    seed_settings: Settings,
) -> None:
    user_repository.exists_user_with_role.return_value = True

    created = seed_super_admin(
        db_session,
        settings=seed_settings,
        user_repository=user_repository,
    )

    assert created is False
    user_repository.create_user.assert_not_called()


def test_seed_skips_when_credentials_not_configured(
    db_session: MagicMock,
    user_repository: MagicMock,
) -> None:
    user_repository.exists_user_with_role.return_value = False
    settings = Settings(
        secret_key="x" * 32,
        super_admin_email=None,
        super_admin_password=None,
        super_admin_first_name=None,
        super_admin_last_name=None,
    )

    created = seed_super_admin(
        db_session,
        settings=settings,
        user_repository=user_repository,
    )

    assert created is False
    user_repository.create_user.assert_not_called()
