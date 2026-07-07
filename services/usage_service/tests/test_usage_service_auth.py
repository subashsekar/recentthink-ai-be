"""Tests for usage service authentication."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from shared.config import get_settings
from shared.security.service_auth import INTERNAL_SERVICE_TOKEN_HEADER


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_record_usage_requires_service_token(client: TestClient) -> None:
    response = client.post(
        "/usage/record",
        json={
            "user_id": str(uuid4()),
            "service_name": "ai_service",
            "feature": "leetcode",
            "request_count": 1,
            "token_usage": 100,
            "execution_time_ms": 500,
        },
    )
    assert response.status_code == 401
    assert "Invalid internal service token" in response.json()["detail"]


def test_record_usage_rejects_invalid_token(client: TestClient) -> None:
    response = client.post(
        "/usage/record",
        json={
            "user_id": str(uuid4()),
            "service_name": "ai_service",
            "feature": "leetcode",
            "request_count": 1,
            "token_usage": 100,
            "execution_time_ms": 500,
        },
        headers={INTERNAL_SERVICE_TOKEN_HEADER: "wrong-token"},
    )
    assert response.status_code == 401


def test_record_usage_accepts_valid_service_token(client: TestClient) -> None:
    from app.dependencies.services import get_usage_service
    from app.main import app
    from app.schemas.usage import RecordUsageResponse

    mock_service = MagicMock()
    record_id = uuid4()
    mock_service.record_usage.return_value = RecordUsageResponse(id=record_id)
    app.dependency_overrides[get_usage_service] = lambda: mock_service
    try:
        response = client.post(
            "/usage/record",
            json={
                "user_id": str(uuid4()),
                "service_name": "ai_service",
                "feature": "leetcode",
                "request_count": 1,
                "token_usage": 100,
                "execution_time_ms": 500,
            },
            headers={INTERNAL_SERVICE_TOKEN_HEADER: get_settings().internal_service_token},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["id"] == str(record_id)
