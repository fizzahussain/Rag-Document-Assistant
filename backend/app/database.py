from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.config import settings
from backend.app.core.logging import logger
from backend.app.models.base import Base

# Build database URL with fallback to SQLite for local standalone development
db_url = settings.DATABASE_URL
if "postgresql" in db_url:
    # Try connecting to PostgreSQL, or fall back to local SQLite if PostgreSQL is not installed/running locally
    try:
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        res = s.connect_ex((settings.POSTGRES_HOST, settings.POSTGRES_PORT))
        s.close()
        if res != 0:
            logger.warning(
                "PostgreSQL port 5432 unreachable. Switching to local SQLite database for standalone mode."
            )
            db_url = "sqlite+aiosqlite:///./data/rag_db.sqlite"
    except Exception:
        db_url = "sqlite+aiosqlite:///./data/rag_db.sqlite"

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Ensures database directory and tables exist on startup."""
    import os

    os.makedirs("./data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
