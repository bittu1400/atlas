"""Database engine, connection lifecycle, and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from atlas.platform.config import get_settings
from sqlalchemy import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def get_async_engine(database_url: str | None = None) -> AsyncEngine:
    """Create and configure async SQLAlchemy engine."""
    settings = get_settings()
    url = database_url or settings.database_url
    return create_async_engine(
        url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        future=True,
    )


def get_sync_engine(database_sync_url: str | None = None) -> Engine:
    """Create synchronous engine for migrations and CLI utilities."""
    settings = get_settings()
    url = database_sync_url or settings.database_sync_url
    return create_engine(url, future=True)


class DatabaseSessionManager:
    """Manager for async database sessions."""

    def __init__(self, engine: AsyncEngine | None = None) -> None:
        self.engine = engine or get_async_engine()
        self.sessionmaker = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Provide a transactional async session block."""
        async with self.sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_session(self) -> AsyncSession:
        """Create and return a new AsyncSession."""
        return self.sessionmaker()

    async def close(self) -> None:
        """Dispose underlying engine pool."""
        await self.engine.dispose()


_session_manager: DatabaseSessionManager | None = None


def get_session_manager() -> DatabaseSessionManager:
    """Get or create singleton DatabaseSessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSessionManager()
    return _session_manager
