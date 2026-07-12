"""Local storage backend tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from shared.storage.base import StorageError
from shared.storage.local import LocalStorageBackend


def test_local_storage_save_url_and_delete(tmp_path: Path) -> None:
    backend = LocalStorageBackend(
        root_dir=tmp_path,
        public_base_url="http://localhost:8002/media",
    )
    url = backend.save(key="avatars/u1/a.jpg", data=b"abc", content_type="image/jpeg")
    assert url == "http://localhost:8002/media/avatars/u1/a.jpg"
    assert (tmp_path / "avatars" / "u1" / "a.jpg").read_bytes() == b"abc"
    assert backend.url_for("avatars/u1/a.jpg") == url
    backend.delete("avatars/u1/a.jpg")
    assert not (tmp_path / "avatars" / "u1" / "a.jpg").exists()


def test_local_storage_rejects_path_traversal(tmp_path: Path) -> None:
    backend = LocalStorageBackend(root_dir=tmp_path, public_base_url="http://x/media")
    with pytest.raises(StorageError):
        backend.save(key="../etc/passwd", data=b"x", content_type="text/plain")
