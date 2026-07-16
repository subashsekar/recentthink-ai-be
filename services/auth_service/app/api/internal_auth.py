"""Internal Auth routes for gateway session enforcement.

Consumed exclusively by the API Gateway via ``X-Internal-Service-Token``.
"""

from __future__ import annotations

from uuid import UUID

from app.database import get_db
from app.dependencies.internal import require_internal_service
from app.dependencies.repositories import get_user_repository
from app.repositories.user_repository import UserRepository
from app.schemas.user_state import UserStateResponse
from app.services.user_state_service import UserStateService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/internal/auth", tags=["internal-auth"])


def get_user_state_service(
    db: Session = Depends(get_db),
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserStateService:
    # ``db`` is injected so the request is bound to a session lifecycle.
    _ = db
    return UserStateService(user_repository=user_repository)


@router.get(
    "/user-state/{user_id}",
    response_model=UserStateResponse,
    dependencies=[Depends(require_internal_service)],
)
def get_user_state(
    user_id: UUID,
    service: UserStateService = Depends(get_user_state_service),
) -> UserStateResponse:
    """Return ``is_active``, ``is_blocked``, ``role``, and ``pwd_ts`` for ``user_id``."""
    return service.get_user_state(user_id)
