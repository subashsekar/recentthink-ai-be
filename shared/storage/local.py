"""Local filesystem storage backend."""

from __future__ import annotations

from pathlib import Path

from shared.storage.base import StorageError


class LocalStorageBackend:
    """Store files under a local directory and expose them via a base URL."""

    def __init__(self, *, root_dir: Path, public_base_url: str) -> None:
        self._root = root_dir
        self._public_base_url = public_base_url.rstrip("/")
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Write bytes to disk and return the public URL."""
        del content_type  # local FS does not persist content-type metadata
        path = self._resolve(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as exc:
            raise StorageError(f"Failed to store object '{key}'.") from exc
        return self.url_for(key)

    def delete(self, key: str) -> None:
        """Delete a local object; missing files are treated as success."""
        path = self._resolve(key)
        try:
            if path.is_file():
                path.unlink()
        except OSError as exc:
            raise StorageError(f"Failed to delete object '{key}'.") from exc

    def url_for(self, key: str) -> str:
        """Build the public URL for ``key``."""
        return f"{self._public_base_url}/{key.lstrip('/')}"

    def _resolve(self, key: str) -> Path:
        """Map an object key to a path under the storage root (no traversal)."""
        cleaned = key.replace("\\", "/").lstrip("/")
        if not cleaned or ".." in cleaned.split("/"):
            raise StorageError("Invalid storage key.")
        path = (self._root / cleaned).resolve()
        try:
            path.relative_to(self._root.resolve())
        except ValueError as exc:
            raise StorageError("Invalid storage key.") from exc
        return path
