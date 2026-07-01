"""SQLAlchemy engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import Generator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


settings = get_settings()


def normalize_database_url(url: str) -> str:
    """Normalize Supabase-style URLs for psycopg3 and SQLAlchemy."""
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)

    parsed = urlparse(url)
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    query_params.pop("pgbouncer", None)
    cleaned_query = urlencode(query_params, doseq=True)
    return urlunparse(parsed._replace(query=cleaned_query))


engine = create_engine(
    normalize_database_url(settings.database_url),
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session]:
    """Yield a database session and ensure it is closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
