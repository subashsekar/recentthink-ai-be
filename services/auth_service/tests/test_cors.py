"""Tests for CORS configuration."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_cors_allows_configured_origin(client: TestClient) -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_does_not_allow_wildcard_origin(client: TestClient) -> None:
    response = client.options(
        "/auth/login",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "*"
    assert allow_origin != "https://evil.example.com"


def test_request_id_header_is_returned(client: TestClient) -> None:
    response = client.get("/health")
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_is_propagated(client: TestClient) -> None:
    custom_id = "custom-request-id-12345"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.headers["X-Request-ID"] == custom_id


def test_cors_origins_rejects_wildcard_in_settings() -> None:
    from pydantic import ValidationError

    from shared.config import Settings

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(cors_origins=["*"])
