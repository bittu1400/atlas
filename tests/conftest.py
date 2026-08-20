"""Pytest fixtures and configuration for Atlas tests."""

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

TEST_DATABASE_URL = os.getenv(
    "ATLAS_TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5432/atlas_test"
)


@pytest_asyncio.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine]:
    """Create test async engine with NullPool."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        future=True,
    )
    # Use alembic for migrations to ensure schema matches production
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("+asyncpg", "+psycopg"))

    # Downgrade to base to clean up everything including alembic_version
    command.downgrade(alembic_cfg, "base")
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")

    yield engine

    command.downgrade(alembic_cfg, "base")
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
