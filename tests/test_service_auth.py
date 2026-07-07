"""Tests for internal service authentication helpers."""

from __future__ import annotations

import pytest

from shared.config import Settings
from shared.exceptions.auth import AuthenticationException
from shared.security.service_auth import verify_internal_service_token


def test_verify_internal_service_token_accepts_valid_token() -> None:
    settings = Settings(internal_service_token="secret-token")
    verify_internal_service_token("secret-token", settings=settings)


def test_verify_internal_service_token_rejects_missing_token() -> None:
    settings = Settings(internal_service_token="secret-token")
    with pytest.raises(AuthenticationException, match="Invalid internal service token"):
        verify_internal_service_token(None, settings=settings)


def test_verify_internal_service_token_rejects_wrong_token() -> None:
    settings = Settings(internal_service_token="secret-token")
    with pytest.raises(AuthenticationException, match="Invalid internal service token"):
        verify_internal_service_token("wrong", settings=settings)


def test_verify_internal_service_token_requires_configuration() -> None:
    settings = Settings.model_construct(internal_service_token="")
    with pytest.raises(AuthenticationException, match="not configured"):
        verify_internal_service_token("anything", settings=settings)
