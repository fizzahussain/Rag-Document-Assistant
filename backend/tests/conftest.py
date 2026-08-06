import os
from collections.abc import Generator
from pathlib import Path

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_rag.sqlite"
os.environ["AUTH_SECRET_KEY"] = "test-only-secret"
os.environ["UPLOAD_DIR"] = "./data/test_uploads"
Path("./data").mkdir(exist_ok=True)
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["LLM_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

from backend.app.database import engine
from backend.app.main import app
from backend.app.models.base import Base


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Generator[None, None, None]:
    import asyncio

    async def create_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)

    async def drop_tables() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)

    asyncio.run(create_tables())
    yield
    asyncio.run(drop_tables())


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client
