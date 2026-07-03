"""RecentThink Auth Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.database import router as database_router
from app.api.exception_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.core.config import SERVICE_NAME
from app.core.rate_limit import limiter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import Environment, get_settings
from shared.database import SessionLocal
from shared.middleware.request_id import RequestIdMiddleware
from shared.monitoring.sentry import init_sentry

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    from app.services.super_admin_seed_service import seed_super_admin

    init_sentry()

    if get_settings().environment is not Environment.TEST:
        db = SessionLocal()
        try:
            seed_super_admin(db)
        finally:
            db.close()
    yield


app = FastAPI(
    title="RecentThink Auth Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Expose the limiter to slowapi's decorators via application state.
app.state.limiter = limiter

# Request correlation for logging and Sentry context.
app.add_middleware(RequestIdMiddleware)

# CORS — explicit origins only; never wildcard.
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
app.include_router(database_router)
app.include_router(auth_router)
app.include_router(admin_router)

# Service name available for logging and monitoring context.
app.state.service_name = SERVICE_NAME
