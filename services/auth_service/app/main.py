"""RecentThink Auth Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.database import router as database_router
from app.api.exception_handlers import register_exception_handlers
from app.api.health import router as health_router
from app.core.rate_limit import limiter
from fastapi import FastAPI

APP_VERSION = "0.1.0"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown hooks."""
    yield


app = FastAPI(
    title="RecentThink Auth Service",
    version=APP_VERSION,
    lifespan=lifespan,
)

# Expose the limiter to slowapi's decorators via application state.
app.state.limiter = limiter

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(database_router)
app.include_router(auth_router)
