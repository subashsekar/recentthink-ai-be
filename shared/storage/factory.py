"""Storage backend factory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.config import get_settings
from shared.storage.base import StorageBackend
from shared.storage.local import LocalStorageBackend
from shared.storage.supabase import SupabaseStorageBackend


@lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    """Return the configured storage backend (cached)."""
    settings = get_settings()
    backend = settings.storage_backend.lower().strip()
    if backend == "local":
        return LocalStorageBackend(
            root_dir=Path(settings.storage_local_path),
            public_base_url=settings.storage_public_base_url,
        )
    if backend == "supabase":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required when "
                "STORAGE_BACKEND=supabase.",
            )
        return SupabaseStorageBackend(
            supabase_url=settings.supabase_url,
            service_role_key=settings.supabase_service_role_key,
            bucket=settings.supabase_storage_bucket,
            public_base_url=settings.storage_public_base_url,
        )
    raise ValueError(
        f"Unsupported STORAGE_BACKEND '{settings.storage_backend}'. "
        "Supported values: local, supabase.",
    )
