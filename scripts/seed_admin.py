"""Seed the default super-administrator account."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from app.services.super_admin_seed_service import seed_super_admin  # noqa: E402

from shared.database import SessionLocal  # noqa: E402


def main() -> None:
    """Insert the default super-admin when one does not already exist."""
    db = SessionLocal()
    try:
        created = seed_super_admin(db)
        if created:
            print("Seeded default super admin.")
        else:
            print("Super admin seed skipped (already exists or not configured).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
