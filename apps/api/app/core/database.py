"""
TraceHarbor API — Async SQLAlchemy Database Engine & Session

Provides the async engine, session factory, and Base class for ORM models.
Configures bounded connection pooling and connection health checks (pre-ping).
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine_kwargs: dict[str, Any] = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

# Configure connection pooling for client-server databases (e.g. Neon PostgreSQL)
if "sqlite" not in settings.database_url:
    engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 5,
            "pool_timeout": 30.0,
            "pool_recycle": 1800,
        }
    )

engine = create_async_engine(settings.database_url, **engine_kwargs)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass


async def get_db() -> AsyncSession:  # type: ignore[misc]
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
