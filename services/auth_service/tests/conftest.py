"""Pytest configuration for the Auth Service test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@pytest.fixture
def service_root() -> Path:
    """Return the Auth Service root directory."""
    return SERVICE_ROOT


@pytest.fixture(autouse=True)
def _disable_rate_limiting() -> object:
    """Disable per-IP rate limiting for the suite.

    All requests from ``TestClient`` share one client IP, so the real limits
    would trip across unrelated tests. Tests that specifically exercise rate
    limiting re-enable the limiter locally.
    """
    from app.core.rate_limit import limiter

    original = limiter.enabled
    limiter.enabled = False
    yield
    limiter.enabled = original
