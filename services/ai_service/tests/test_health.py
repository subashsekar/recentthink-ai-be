"""Health endpoint smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the AI Service."""
    from app.main import app

    return TestClient(app)


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """GET / should return HTTP 200 with service health payload."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ai_service"
    assert data["status"] == "healthy"
