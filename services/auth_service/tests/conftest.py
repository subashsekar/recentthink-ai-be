"""Pytest configuration for the Auth Service test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def service_root() -> Path:
    """Return the Auth Service root directory."""
    return SERVICE_ROOT
