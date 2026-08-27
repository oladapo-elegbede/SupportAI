import pytest
from typing import AsyncGenerator
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.config import settings

# Dedicated Test Engine with NullPool to prevent connection pool conflicts
test_engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,
    future=True,
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provides an isolated async database session for each test."""
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.close()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provides an async HTTP client for testing FastAPI endpoints natively."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
