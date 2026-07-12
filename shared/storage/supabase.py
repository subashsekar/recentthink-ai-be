"""Supabase Storage backend for public object uploads."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from shared.storage.base import StorageError


class SupabaseStorageBackend:
    """Store files in a Supabase Storage bucket via the REST API.

    Uses the service-role key server-side. Public read URLs are returned so
    avatars can be rendered directly in the browser.
    """

    def __init__(
        self,
        *,
        supabase_url: str,
        service_role_key: str,
        bucket: str,
        public_base_url: str | None = None,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = supabase_url.rstrip("/")
        self._service_role_key = service_role_key
        self._bucket = bucket.strip("/")
        self._public_base_url = (
            public_base_url.rstrip("/")
            if public_base_url
            else f"{self._base_url}/storage/v1/object/public/{self._bucket}"
        )
        self._timeout = timeout_seconds
        self._client = client

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        """Upload (upsert) an object and return its public URL."""
        object_key = key.lstrip("/")
        url = f"{self._base_url}/storage/v1/object/{self._bucket}/{object_key}"
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true",
        }
        try:
            with self._http() as client:
                response = client.post(url, content=data, headers=headers)
            if response.status_code >= 400:
                raise StorageError(
                    f"Supabase upload failed ({response.status_code}): {response.text}",
                )
        except httpx.HTTPError as exc:
            raise StorageError(f"Failed to upload object '{object_key}'.") from exc
        return self.url_for(object_key)

    def delete(self, key: str) -> None:
        """Delete an object; missing objects are treated as success."""
        object_key = key.lstrip("/")
        url = f"{self._base_url}/storage/v1/object/{self._bucket}"
        headers = {
            "Authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
            "Content-Type": "application/json",
        }
        try:
            with self._http() as client:
                response = client.delete(
                    url,
                    headers=headers,
                    json={"prefixes": [object_key]},
                )
            # 404 / empty result means already gone.
            if response.status_code >= 400 and response.status_code != 404:
                raise StorageError(
                    f"Supabase delete failed ({response.status_code}): {response.text}",
                )
        except httpx.HTTPError as exc:
            raise StorageError(f"Failed to delete object '{object_key}'.") from exc

    def url_for(self, key: str) -> str:
        """Return the public URL for ``key``."""
        return f"{self._public_base_url}/{key.lstrip('/')}"

    @contextmanager
    def _http(self) -> Iterator[httpx.Client]:
        if self._client is not None:
            yield self._client
            return
        with httpx.Client(timeout=self._timeout) as client:
            yield client
