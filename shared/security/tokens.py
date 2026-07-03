"""Opaque token hashing utilities.

Refresh tokens are high-value, long-lived credentials. They must never be
persisted in plaintext: a database compromise would otherwise hand an attacker
every active session. We store only a SHA-256 digest and compare digests on
lookup, mirroring how password hashes are handled.

SHA-256 (rather than bcrypt) is appropriate here because refresh tokens are
already high-entropy random values (``secrets.token_urlsafe``), so they are not
susceptible to brute-force/dictionary attacks the way human-chosen passwords
are. A fast, deterministic digest lets us index and look tokens up directly.
"""

from __future__ import annotations

import hashlib


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of an opaque token string."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
