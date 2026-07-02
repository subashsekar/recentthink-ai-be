"""RecentThink Auth Service ASGI application entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.api.database import router as database_router
from app.api.health import router as health_router
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

app.include_router(health_router)
app.include_router(database_router)
