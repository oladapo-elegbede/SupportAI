import pytest
from typing import AsyncGenerator
import httpx

from app.main import app
from app.core.database import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean async database session for unit tests."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provides an async HTTP client for testing FastAPI endpoints natively."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
