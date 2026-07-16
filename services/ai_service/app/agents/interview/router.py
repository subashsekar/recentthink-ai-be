"""Interview prep agent module (scaffold only — intentionally not implemented)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/interview", tags=["interview"])


@router.get("/health")
def interview_health() -> dict[str, str]:
    """Scaffold health endpoint — Interview Trainer remains out of scope."""
    return {
        "status": "scaffold",
        "product": "interview",
        "available": "false",
        "detail": "Interview Trainer is not implemented in this portfolio release.",
    }
