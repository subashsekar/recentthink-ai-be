"""Shared file-storage abstractions for microservices."""

from shared.storage.base import StorageBackend, StorageError
from shared.storage.factory import get_storage
from shared.storage.local import LocalStorageBackend
from shared.storage.supabase import SupabaseStorageBackend

__all__ = [
    "LocalStorageBackend",
    "StorageBackend",
    "StorageError",
    "SupabaseStorageBackend",
    "get_storage",
]
