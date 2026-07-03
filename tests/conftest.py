"""Shared pytest fixtures and configuration for the RecentThink test suite."""

from __future__ import annotations

import os

import pytest

from shared.config import Settings


@pytest.fixture(autouse=True)
def _force_test_environment() -> None:
    """Force the ``ENVIRONMENT`` variable to ``test`` for every test."""
    os.environ["ENVIRONMENT"] = "test"
    from shared.config import get_settings

    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """Return a freshly built :class:`Settings` instance for tests."""
    return Settings()
