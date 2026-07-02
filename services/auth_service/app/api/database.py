"""Database connectivity health routes."""

from __future__ import annotations

from app.database import get_db
from app.schemas.common import MessageResponse
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/db", response_model=MessageResponse)
def verify_database_connection(db: Session = Depends(get_db)) -> MessageResponse:
    """Verify that the service can reach the configured database."""
    db.execute(text("SELECT 1"))
    return MessageResponse(message="Database Connected Successfully")
