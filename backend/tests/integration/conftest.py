"""
Integration test infrastructure.

Requires TEST_DATABASE_URL pointing to a real PostgreSQL database.
All integration tests are skipped when that var is absent (enforced in root conftest.py).

Architecture:
- test_engine: session-scoped async engine on the test DB
- client: session-scoped AsyncClient against the FastAPI app
- db_session: function-scoped session for inserting test fixtures
- clear_tables: autouse fixture that truncates all tables between tests
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database import Base, get_db

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")


# Build a test app without the lifespan (no migrations, no seed, no tectonic warmup).
# This keeps integration tests fast and deterministic.
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth import verify_api_key
from app.routers import jobs, profile

_limiter = Limiter(key_func=get_remote_address)

_test_app = FastAPI()
_test_app.state.limiter = _limiter
_test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_auth = [Depends(verify_api_key)]
_test_app.include_router(profile.router, prefix="/admin", dependencies=_auth)
_test_app.include_router(jobs.router, prefix="/admin", dependencies=_auth)


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def client(test_engine):
    _session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _override_get_db():
        async with _session_factory() as session:
            yield session

    _test_app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=_test_app), base_url="http://test") as ac:
        yield ac
    _test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    _session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with _session_factory() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def clear_tables(test_engine):
    """Truncate all rows between tests so each test starts clean."""
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
