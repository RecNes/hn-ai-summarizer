"""Database setup with SQLAlchemy for both async and sync operations."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.ASYNC_DATABASE_URL, echo=settings.DB_ECHO, future=True
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL, echo=settings.DB_ECHO, future=True
)

SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)

Base = declarative_base()


async def get_db():
    """Dependency to get async database session."""
    
    async with AsyncSessionLocal() as session:
        yield session
        await session.commit()
