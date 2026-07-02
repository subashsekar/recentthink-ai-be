"""Seed the default system administrator account."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUTH_SERVICE_ROOT = REPO_ROOT / "services" / "auth_service"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(AUTH_SERVICE_ROOT))

from app.models.admin import Admin  # noqa: E402
from sqlalchemy import select  # noqa: E402

from shared.database import SessionLocal  # noqa: E402
from shared.security import hash_password  # noqa: E402

DEFAULT_ADMIN_EMAIL = "admin@recentthink.ai"
DEFAULT_ADMIN_FIRST_NAME = "System"
DEFAULT_ADMIN_LAST_NAME = "Administrator"
DEFAULT_ADMIN_PASSWORD = os.getenv("SEED_ADMIN_PASSWORD", "Admin@12345")


def seed_admin() -> None:
    """Insert the default administrator when one does not already exist."""
    db = SessionLocal()
    try:
        existing = db.scalar(
            select(Admin).where(Admin.email == DEFAULT_ADMIN_EMAIL),
        )
        if existing is not None:
            print(f"Admin already exists: {DEFAULT_ADMIN_EMAIL}")
            return

        admin = Admin(
            email=DEFAULT_ADMIN_EMAIL,
            password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
            first_name=DEFAULT_ADMIN_FIRST_NAME,
            last_name=DEFAULT_ADMIN_LAST_NAME,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Seeded default admin: {DEFAULT_ADMIN_EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
