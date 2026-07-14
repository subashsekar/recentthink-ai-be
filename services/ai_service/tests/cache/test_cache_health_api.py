"""HTTP tests for GET /cache/health."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_cache_health_endpoint() -> None:
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/cache/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"healthy", "disabled"}
    assert "entry_count" in body
    assert "memory_usage_bytes" in body
    assert "ttl" in body
