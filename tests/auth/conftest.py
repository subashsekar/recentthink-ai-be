"""Pytest fixtures for auth API integration tests."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AUTH_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from shared.database import engine  # noqa: E402


@pytest.fixture(autouse=True)
def _reload_auth_service_models() -> Iterator[None]:
    """Re-register ORM mappers after auth-service unit tests clear them."""
    app_modules = [
        name for name in list(sys.modules) if name == "app" or name.startswith("app.")
    ]
    for name in app_modules:
        sys.modules.pop(name, None)

    if app_modules:
        from sqlalchemy.orm import clear_mappers

        from shared.database import Base

        clear_mappers()
        Base.metadata.clear()

    auth_service_root_str = str(AUTH_SERVICE_ROOT)
    if auth_service_root_str not in sys.path:
        sys.path.insert(0, auth_service_root_str)

    import app.models  # noqa: F401

    yield


@pytest.fixture
def db_session() -> Iterator[Session]:
    """Yield a database session that rolls back all changes after each test.

    ``join_transaction_mode="create_savepoint"`` ensures commits issued by the
    application under test target a SAVEPOINT, so the outer rollback undoes all
    changes and integration tests never leave data behind.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
