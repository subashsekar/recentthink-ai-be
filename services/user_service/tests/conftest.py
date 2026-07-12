"""Pytest configuration for the User Service test suite."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@pytest.fixture
def service_root() -> Path:
    """Return the User Service root directory."""
    return SERVICE_ROOT


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def auth_user(user_id):
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(user_id=user_id, email="user@example.com", role="USER")


@pytest.fixture
def admin_user():
    from app.dependencies.auth import AuthenticatedUser

    return AuthenticatedUser(user_id=uuid4(), email="admin@example.com", role="ADMIN")
