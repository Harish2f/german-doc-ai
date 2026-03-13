import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.main import app
from src.db.postgres import Base, get_db
from src.dependencies import verify_api_key

VALID_API_KEY= "dev-secret-key"
HEADERS = {"x-api-key":VALID_API_KEY}

# use SQLite in-memory databases for tests - no docker needed
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine= create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False,
    autoflush=True
)

async def override_get_db():
    """Replace PostgreSQL with SQLite for tests."""
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
            await session.flush()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
def reset_test_db():
    """Drop and recreate all tables before each test."""
    import asyncio
    asyncio.get_event_loop().run_until_complete(
        _reset_db()
    )
    yield
    asyncio.get_event_loop().run_until_complete(
        _reset_db()
    )


async def _reset_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

@pytest.fixture
def client():
    """FastAPI Test client with database override."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Valid API key Headers available to all tests"""
    return HEADERS