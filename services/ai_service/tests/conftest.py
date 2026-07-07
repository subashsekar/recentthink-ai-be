"""Pytest configuration for the AI Service test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@pytest.fixture(autouse=True)
def _disable_rate_limiting() -> object:
    from app.core.rate_limit import limiter

    previous = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = previous


@pytest.fixture
def service_root() -> Path:
    """Return the AI Service root directory."""
    return SERVICE_ROOT
