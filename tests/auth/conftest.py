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
