"""Gateway proxy error helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpstreamError:
    status_code: int
    detail: str

