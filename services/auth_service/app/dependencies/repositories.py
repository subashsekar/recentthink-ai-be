"""FastAPI dependencies for repository injection."""

from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository


def get_admin_repository(db: Session = Depends(get_db)) -> AdminRepository:
    """Provide an :class:`AdminRepository` bound to the request session."""
    return AdminRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    """Provide a :class:`UserRepository` bound to the request session."""
    return UserRepository(db)
