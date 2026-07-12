"""RecentThink User Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.api.exception_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.api.internal_admin import router as internal_admin_router
from app.api.profile import router as profile_router
from app.core.config import SERVICE_NAME
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from shared.config import get_settings
from shared.middleware.request_id import RequestIdMiddleware
from shared.monitoring.sentry import init_sentry

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    init_sentry()
    settings = get_settings()
    Path(settings.storage_local_path).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="RecentThink User Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(RequestIdMiddleware)

_cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cfg.cors_origins,
    allow_credentials=_cfg.cors_allow_credentials,
    allow_methods=_cfg.cors_allow_methods,
    allow_headers=_cfg.cors_allow_headers,
    expose_headers=["X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(profile_router)
app.include_router(internal_admin_router)

# Serve locally stored media (avatars) in development.
_media_root = Path(_cfg.storage_local_path)
_media_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_root)), name="media")

app.state.service_name = SERVICE_NAME
