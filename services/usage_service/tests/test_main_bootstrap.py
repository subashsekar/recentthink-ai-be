"""Usage Service bootstrap and middleware tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_usage_service_exposes_request_id_header() -> None:
    from app.main import app

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_usage_service_registers_core_exception_handlers() -> None:
    from app.api.exception_handlers import register_exception_handlers
    from fastapi import FastAPI
    from shared.exceptions.repository import RecordNotFoundError

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/missing")
    def missing() -> None:
        raise RecordNotFoundError("Usage record not found.")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Usage record not found."
