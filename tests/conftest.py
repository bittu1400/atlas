"""Pytest fixtures and configuration for Atlas tests."""

from collections.abc import AsyncGenerator

import pytest_asyncio
from atlas.adapters.persistence.tables import Base
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = "postgresql+asyncpg://postgres@localhost:5432/atlas_test"


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create test async engine with NullPool."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Provide an isolated database session rolled back after each test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
