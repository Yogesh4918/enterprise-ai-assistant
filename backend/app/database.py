"""Async SQLAlchemy engine, session factory, and database dependency."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

import os
from app.config import get_settings

settings = get_settings()

if settings.DATABASE_URL.startswith("sqlite"):
    # sqlite+aiosqlite:///./data/app.db -> ./data/app.db
    # sqlite+aiosqlite:////app/data/app.db -> /app/data/app.db
    # sqlite+aiosqlite:///app.db -> app.db
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    # Remove leading slash if it exists but it was double-slash relative path
    # e.g., sqlite+aiosqlite:///./data/app.db
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine_options = {
    "echo": settings.DEBUG,
}

if not settings.DATABASE_URL.startswith("sqlite"):
    engine_options["pool_size"] = 20
    engine_options["max_overflow"] = 10
    engine_options["pool_pre_ping"] = True
    engine_options["pool_recycle"] = 300

engine = create_async_engine(
    settings.DATABASE_URL,
    **engine_options
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables defined by ORM models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the connection pool."""
    await engine.dispose()
