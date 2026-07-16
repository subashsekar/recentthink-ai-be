"""Supabase storage backend unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from shared.storage.base import StorageError
from shared.storage.supabase import SupabaseStorageBackend


def test_supabase_save_upserts_and_returns_public_url() -> None:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 200
    response.text = "ok"
    client.post.return_value = response

    backend = SupabaseStorageBackend(
        supabase_url="https://abc.supabase.co",
        service_role_key="service-role",
        bucket="recenthink_user_profile_picture",
        client=client,
    )
    url = backend.save(
        key="avatars/u1/a.jpg",
        data=b"\xff\xd8\xff",
        content_type="image/jpeg",
    )
    assert url == (
        "https://abc.supabase.co/storage/v1/object/public/"
        "recenthink_user_profile_picture/avatars/u1/a.jpg"
    )
    client.post.assert_called_once()
    args, kwargs = client.post.call_args
    assert "recenthink_user_profile_picture/avatars/u1/a.jpg" in args[0]
    assert kwargs["headers"]["x-upsert"] == "true"
    assert kwargs["headers"]["Authorization"] == "Bearer service-role"


def test_supabase_save_raises_on_http_error() -> None:
    client = MagicMock()
    response = MagicMock()
    response.status_code = 400
    response.text = "bad request"
    client.post.return_value = response
    backend = SupabaseStorageBackend(
        supabase_url="https://abc.supabase.co",
        service_role_key="key",
        bucket="recenthink_user_profile_picture",
        client=client,
    )
    with pytest.raises(StorageError, match="upload failed"):
        backend.save(key="a.jpg", data=b"x", content_type="image/jpeg")


def test_supabase_save_raises_on_transport_error() -> None:
    client = MagicMock()
    client.post.side_effect = httpx.ConnectError("down")
    backend = SupabaseStorageBackend(
        supabase_url="https://abc.supabase.co",
        service_role_key="key",
        bucket="recenthink_user_profile_picture",
        client=client,
    )
    with pytest.raises(StorageError, match="Failed to upload"):
        backend.save(key="a.jpg", data=b"x", content_type="image/jpeg")


def test_supabase_delete_success_and_404() -> None:
    client = MagicMock()
    ok = MagicMock(status_code=200, text="ok")
    missing = MagicMock(status_code=404, text="missing")
    client.delete.side_effect = [ok, missing]
    backend = SupabaseStorageBackend(
        supabase_url="https://abc.supabase.co",
        service_role_key="key",
        bucket="recenthink_user_profile_picture",
        client=client,
    )
    backend.delete("avatars/u1/a.jpg")
    backend.delete("avatars/u1/gone.jpg")
    assert client.delete.call_count == 2
    _, kwargs = client.delete.call_args
    assert kwargs["json"] == {"prefixes": ["avatars/u1/gone.jpg"]}


def test_supabase_delete_raises_on_error() -> None:
    client = MagicMock()
    client.delete.return_value = MagicMock(status_code=500, text="err")
    backend = SupabaseStorageBackend(
        supabase_url="https://abc.supabase.co",
        service_role_key="key",
        bucket="recenthink_user_profile_picture",
        client=client,
    )
    with pytest.raises(StorageError, match="delete failed"):
        backend.delete("a.jpg")


def test_get_storage_supabase(monkeypatch) -> None:
    from shared.storage.factory import get_storage
    from shared.storage.supabase import SupabaseStorageBackend

    get_storage.cache_clear()
    monkeypatch.setenv("STORAGE_BACKEND", "supabase")
    monkeypatch.setenv("STORAGE_PUBLIC_BASE_URL", "")
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "recenthink_user_profile_picture")
    from shared.config import get_settings

    get_settings.cache_clear()
    try:
        storage = get_storage()
        assert isinstance(storage, SupabaseStorageBackend)
        assert "recenthink_user_profile_picture" in storage.url_for("x.jpg")
    finally:
        get_storage.cache_clear()
        get_settings.cache_clear()
