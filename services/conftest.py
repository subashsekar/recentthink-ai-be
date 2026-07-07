"""Pytest configuration for microservice test suites."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = REPO_ROOT / "services"
_ACTIVE_SERVICE_ROOT: Path | None = None


def _configure_sys_path(service_root: Path) -> None:
    """Ensure only the target service root is first on ``sys.path``."""
    for sibling in SERVICES_DIR.iterdir():
        if not sibling.is_dir():
            continue
        sibling_str = str(sibling)
        while sibling_str in sys.path:
            sys.path.remove(sibling_str)

    service_root_str = str(service_root)
    if service_root_str not in sys.path:
        sys.path.insert(0, service_root_str)


def service_import_setup(service_root: Path) -> None:
    """Reset ``app`` imports and ``sys.path`` without touching ORM metadata."""
    global _ACTIVE_SERVICE_ROOT

    if _ACTIVE_SERVICE_ROOT == service_root:
        _configure_sys_path(service_root)
        return

    app_modules = [
        name for name in list(sys.modules) if name == "app" or name.startswith("app.")
    ]
    for name in app_modules:
        sys.modules.pop(name, None)

    _ACTIVE_SERVICE_ROOT = service_root
    _configure_sys_path(service_root)


def service_test_setup(service_root: Path) -> None:
    """Prepare ``sys.path``, module cache, and ORM state for a service test."""
    global _ACTIVE_SERVICE_ROOT

    app_modules = [
        name for name in list(sys.modules) if name == "app" or name.startswith("app.")
    ]
    for name in app_modules:
        sys.modules.pop(name, None)

    if app_modules:
        from sqlalchemy.orm import clear_mappers

        from shared.database import Base

        clear_mappers()
        Base.registry.dispose()
        Base.metadata.clear()

    _ACTIVE_SERVICE_ROOT = service_root
    _configure_sys_path(service_root)


def _service_root_for_path(path: Path) -> Path | None:
    """Resolve the microservice root for a collected test path, if any."""
    parts = path.parts
    try:
        services_idx = parts.index("services")
    except ValueError:
        return None
    if services_idx + 1 >= len(parts):
        return None
    service_root = SERVICES_DIR / parts[services_idx + 1]
    if not service_root.is_dir() or not (service_root / "app").is_dir():
        return None
    return service_root


@pytest.hookimpl(tryfirst=True)
def pytest_collectstart(collector: pytest.Collector) -> None:
    """Isolate ``app`` imports before each service test module is collected."""
    path = getattr(collector, "path", None)
    if path is None:
        fspath = getattr(collector, "fspath", None)
        if fspath is None:
            return
        path = Path(str(fspath))
    else:
        path = Path(str(path))

    service_root = _service_root_for_path(path)
    if service_root is not None:
        service_import_setup(service_root)


@pytest.fixture(autouse=True)
def _isolate_service_app_module(service_root: Path) -> Iterator[None]:
    """Prevent cross-service ``app`` package collisions during the test run."""
    service_test_setup(service_root)
    yield
    service_test_setup(service_root)
