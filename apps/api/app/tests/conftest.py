"""
TraceHarbor API — Pytest Configuration, In-Memory DB & Fixtures
"""

import hashlib
import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.api_key import ApiKey
from app.models.project import Project
from app.models.user import User

# In-memory SQLite async engine for fast, isolated, zero-dependency unit and API tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

TEST_API_KEY = "th_live_test_secret_key_12345"
TEST_API_KEY_HASH = hashlib.sha256(TEST_API_KEY.encode("utf-8")).hexdigest()

REVOKED_API_KEY = "th_live_revoked_key_99999"
REVOKED_API_KEY_HASH = hashlib.sha256(REVOKED_API_KEY.encode("utf-8")).hexdigest()

OTHER_PROJECT_API_KEY = "th_live_other_project_key_77777"
OTHER_PROJECT_API_KEY_HASH = hashlib.sha256(OTHER_PROJECT_API_KEY.encode("utf-8")).hexdigest()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create all database tables and seed test accounts before each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # 1. Primary Test User & Project
        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email="test@traceharbor.local",
            password_hash="$2b$12$fakehashforunitestsonly",
            display_name="Test Developer",
        )
        session.add(user)

        project_id = uuid.uuid4()
        project = Project(
            id=project_id,
            user_id=user_id,
            name="Primary Test Project",
        )
        session.add(project)

        # Active Key
        api_key = ApiKey(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Active Test Key",
            key_hash=TEST_API_KEY_HASH,
            key_prefix="th_live_",
            is_active=True,
        )
        session.add(api_key)

        # Revoked Key
        revoked_key = ApiKey(
            id=uuid.uuid4(),
            project_id=project_id,
            name="Revoked Key",
            key_hash=REVOKED_API_KEY_HASH,
            key_prefix="th_live_",
            is_active=False,
        )
        session.add(revoked_key)

        # 2. Secondary Project (for tenant isolation tests)
        other_project_id = uuid.uuid4()
        other_project = Project(
            id=other_project_id,
            user_id=user_id,
            name="Secondary Isolated Project",
        )
        session.add(other_project)

        other_key = ApiKey(
            id=uuid.uuid4(),
            project_id=other_project_id,
            name="Other Project Key",
            key_hash=OTHER_PROJECT_API_KEY_HASH,
            key_prefix="th_live_",
            is_active=True,
        )
        session.add(other_key)

        await session.commit()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestingSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client for FastAPI application with test server base URL."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
