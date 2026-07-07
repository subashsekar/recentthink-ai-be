"""Pytest configuration for the Usage Service test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))


@pytest.fixture
def service_root() -> Path:
    """Return the Usage Service root directory."""
    return SERVICE_ROOT
