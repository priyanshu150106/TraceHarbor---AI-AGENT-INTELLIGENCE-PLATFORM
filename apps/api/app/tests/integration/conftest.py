"""
PostgreSQL & pgvector Integration Test Fixtures.

Automatically detects PostgreSQL availability. If unreachable (e.g. Docker not running),
skips integration tests with an informative message. When PostgreSQL is available,
creates an isolated test database session for real database integration testing.
"""

import asyncio
import contextlib
import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base
from app.models.api_key import ApiKey
from app.models.project import Project
from app.models.user import User

# Default connection URL for integration tests
POSTGRES_TEST_URL = os.getenv(
    "POSTGRES_TEST_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://th:change_me_in_production@127.0.0.1:5432/traceharbor_test",
    ),
)


def _probe_postgres(url: str) -> tuple[bool, str]:
    """Synchronously probe whether PostgreSQL is reachable with a short timeout."""
    async def _async_probe() -> tuple[bool, str]:
        engine: AsyncEngine | None = None
        try:
            engine = create_async_engine(
                url,
                connect_args={"timeout": 2.0},
                pool_pre_ping=True,
            )
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, "Reachable"
        except Exception as e:
            return False, f"Cannot connect to PostgreSQL at {url}: {e}"
        finally:
            if engine:
                await engine.dispose()

    try:
        return asyncio.run(_async_probe())
    except Exception as e:
        return False, str(e)


# Check PostgreSQL availability once at module load
PG_AVAILABLE, PG_REASON = _probe_postgres(POSTGRES_TEST_URL)

# Shared integration engine (only created if PG is available)
pg_test_engine: AsyncEngine | None = None
if PG_AVAILABLE:
    pg_test_engine = create_async_engine(
        POSTGRES_TEST_URL,
        echo=False,
        pool_pre_ping=True,
    )
    PgSessionLocal = async_sessionmaker(
        pg_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
else:
    PgSessionLocal = None  # type: ignore[assignment]


@pytest.fixture(scope="session")
def require_postgres() -> None:
    """Fixture to mandate PostgreSQL availability for integration tests."""
    if not PG_AVAILABLE:
        pytest.skip(
            f"PostgreSQL is not available: {PG_REASON}. "
            f"Run 'docker compose -f infra/docker-compose.yml up -d' to enable real integration tests."
        )


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """
    Override root SQLite autouse fixture for the integration/ directory.
    When PostgreSQL is available, ensures all tables exist on PostgreSQL.
    """
    if not PG_AVAILABLE:
        yield
        return

    assert pg_test_engine is not None
    async with pg_test_engine.begin() as conn:
        # Try enabling pgvector extension
        with contextlib.suppress(Exception):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Clean up tables after session
    async with pg_test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def pg_session(require_postgres: None) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated AsyncSession bound to real PostgreSQL."""
    assert PgSessionLocal is not None
    async with PgSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def seeded_pg_project(
    pg_session: AsyncSession,
) -> tuple[User, Project, ApiKey]:
    """Seed a basic user, project, and active API key in PostgreSQL."""
    user = User(
        id=uuid.uuid4(),
        email=f"pg_test_{uuid.uuid4().hex[:6]}@traceharbor.local",
        password_hash="$2b$12$fakehashforpgintegrationtests",
        display_name="PG Test User",
    )
    pg_session.add(user)

    project = Project(
        id=uuid.uuid4(),
        user_id=user.id,
        name="PG Integration Test Project",
    )
    pg_session.add(project)

    api_key = ApiKey(
        id=uuid.uuid4(),
        project_id=project.id,
        name="PG Test Key",
        key_hash=uuid.uuid4().hex,
        key_prefix="th_live_",
        is_active=True,
    )
    pg_session.add(api_key)

    await pg_session.commit()
    await pg_session.refresh(user)
    await pg_session.refresh(project)
    await pg_session.refresh(api_key)

    return user, project, api_key
