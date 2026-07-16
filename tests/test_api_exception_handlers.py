"""Tests for shared API exception handler utilities."""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from shared.api.exception_handlers import (
    INTERNAL_ERROR_DETAIL,
    error_response,
    register_core_exception_handlers,
    register_rate_limit_handler,
    request_context,
    validation_error_detail,
)
from shared.exceptions.auth import AuthenticationException, ForbiddenError
from shared.exceptions.base import BusinessException, ValidationException
from shared.exceptions.repository import RecordNotFoundError, RepositoryError


def test_error_response_includes_optional_code() -> None:
    response = error_response(
        status_code=400,
        detail="Bad request",
        code="BAD_REQUEST",
    )
    assert response.status_code == 400
    assert json.loads(response.body) == {
        "detail": "Bad request",
        "code": "BAD_REQUEST",
    }


def test_request_context_includes_request_id() -> None:
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
        }
    )
    request.state.request_id = "req-123"

    assert request_context(request) == {
        "endpoint": "/health",
        "request_id": "req-123",
    }


def test_validation_error_detail_uses_first_message() -> None:
    exc = RequestValidationError(
        errors=[{"loc": ("body", "email"), "msg": "field required", "type": "missing"}],
    )
    assert validation_error_detail(exc) == "field required"


def test_register_core_exception_handlers_maps_domain_errors() -> None:
    app = FastAPI()
    register_core_exception_handlers(app)

    @app.get("/missing")
    def missing() -> None:
        raise RecordNotFoundError("Not found.")

    @app.get("/forbidden")
    def forbidden() -> None:
        raise ForbiddenError("Denied.")

    @app.get("/business")
    def business() -> None:
        raise BusinessException("Invalid state", code="INVALID_STATE")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("unexpected")

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/missing").status_code == 404
    assert client.get("/forbidden").status_code == 403
    body = client.get("/business").json()
    assert body["detail"] == "Invalid state"
    assert body["code"] == "INVALID_STATE"
    assert client.get("/boom").status_code == 500
    assert client.get("/boom").json()["detail"] == INTERNAL_ERROR_DETAIL


def test_register_core_exception_handlers_supports_custom_validation_status() -> None:
    app = FastAPI()
    register_core_exception_handlers(app, validation_status_code=422)

    @app.get("/validate")
    def validate() -> None:
        raise ValidationException("Invalid input.")

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/validate").status_code == 422


def test_register_rate_limit_handler_registers_handler() -> None:
    pytest.importorskip("slowapi")
    from slowapi.errors import RateLimitExceeded

    app = FastAPI()
    register_rate_limit_handler(app)
    assert RateLimitExceeded in app.exception_handlers


class _Payload(BaseModel):
    value: int = Field(ge=1)


def test_request_validation_error_maps_to_422() -> None:
    app = FastAPI()
    register_core_exception_handlers(app)

    @app.post("/payload")
    def payload(body: _Payload) -> dict[str, int]:
        return {"value": body.value}

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/payload", json={"value": 0})
    assert response.status_code == 422
    assert "detail" in response.json()


def test_authentication_exception_includes_code() -> None:
    app = FastAPI()
    register_core_exception_handlers(app)

    @app.get("/auth")
    def auth() -> None:
        raise AuthenticationException("Unauthorized", code="AUTH_REQUIRED")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/auth")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_REQUIRED"


def test_repository_error_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    register_core_exception_handlers(app)

    @app.get("/repo")
    def repo() -> None:
        raise RepositoryError("db down")

    with caplog.at_level(logging.ERROR):
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/repo")

    assert response.status_code == 500
    assert "Repository error" in caplog.text
