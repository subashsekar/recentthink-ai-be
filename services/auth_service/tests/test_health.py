"""Health endpoint smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the Auth Service."""
    from app.main import app

    return TestClient(app)


def test_database_endpoint_returns_200(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """GET / should return HTTP 200 when the database is reachable."""
    mock_db = MagicMock(spec=Session)
    mock_db.execute.return_value = None

    def override_get_db() -> Session:
        yield mock_db

    from app.database import get_db
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"message": "Database Connected Successfully"}


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """GET /health should return HTTP 200 with service health payload."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "auth_service"
    assert data["status"] == "healthy"
