"""Pytest configuration for microservice test suites."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = REPO_ROOT / "services"


def service_test_setup(service_root: Path) -> None:
    """Prepare ``sys.path`` and module cache for an isolated service import."""
    app_modules = [
        name for name in list(sys.modules) if name == "app" or name.startswith("app.")
    ]
    for name in app_modules:
        sys.modules.pop(name, None)

    for sibling in SERVICES_DIR.iterdir():
        if not sibling.is_dir():
            continue
        sibling_str = str(sibling)
        while sibling_str in sys.path:
            sys.path.remove(sibling_str)

    service_root_str = str(service_root)
    if service_root_str not in sys.path:
        sys.path.insert(0, service_root_str)


@pytest.fixture(autouse=True)
def _isolate_service_app_module(service_root: Path) -> Iterator[None]:
    """Prevent cross-service ``app`` package collisions during the test run."""
    service_test_setup(service_root)
    yield
    service_test_setup(service_root)
