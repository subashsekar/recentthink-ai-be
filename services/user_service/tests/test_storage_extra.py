"""Additional coverage for storage factory and edge validators."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from shared.exceptions.base import ValidationException
from shared.storage.base import StorageError


def test_get_storage_local(tmp_path: Path, monkeypatch) -> None:
    from shared.storage.factory import get_storage

    get_storage.cache_clear()
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "http://localhost:8002/media")
    from shared.config import get_settings

    get_settings.cache_clear()
    try:
        storage = get_storage()
        url = storage.save(key="t.txt", data=b"hi", content_type="text/plain")
        assert url.endswith("/t.txt")
    finally:
        get_storage.cache_clear()
        get_settings.cache_clear()


def test_get_storage_unsupported(monkeypatch) -> None:
    from shared.storage.factory import get_storage

    get_storage.cache_clear()
    with patch("shared.storage.factory.get_settings") as settings:
        settings.return_value.storage_backend = "s3"
        with pytest.raises(ValueError, match="Unsupported STORAGE_BACKEND"):
            get_storage()
    get_storage.cache_clear()


def test_get_storage_supabase_requires_credentials() -> None:
    from shared.storage.factory import get_storage

    get_storage.cache_clear()
    with patch("shared.storage.factory.get_settings") as settings:
        settings.return_value.storage_backend = "supabase"
        settings.return_value.supabase_url = None
        settings.return_value.supabase_service_role_key = None
        with pytest.raises(ValueError, match="SUPABASE_URL"):
            get_storage()
    get_storage.cache_clear()


def test_local_storage_delete_missing(tmp_path: Path) -> None:
    from shared.storage.local import LocalStorageBackend

    backend = LocalStorageBackend(root_dir=tmp_path, public_base_url="http://x/media")
    backend.delete("missing.jpg")


def test_local_storage_save_oserror(tmp_path: Path) -> None:
    from shared.storage.local import LocalStorageBackend

    backend = LocalStorageBackend(root_dir=tmp_path, public_base_url="http://x/media")
    with patch.object(Path, "write_bytes", side_effect=OSError("disk full")):
        with pytest.raises(StorageError):
            backend.save(key="a.jpg", data=b"x", content_type="image/jpeg")


def test_validators_extra_branches() -> None:
    from app.utils.validators import (
        normalize_platform_username,
        validate_bio,
        validate_http_url,
        validate_linkedin_url,
    )

    with pytest.raises(ValidationException):
        normalize_platform_username("bad!", field="github_username")
    with pytest.raises(ValidationException):
        validate_http_url("notaurl", field="portfolio_url")
    assert validate_linkedin_url(None) is None
    assert validate_bio(None) is None
