"""
Database session management.
Handles SQLite connection and session lifecycle with async support.
"""
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings

settings = get_settings()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Enable foreign key constraints for SQLite.
    This is required for proper referential integrity.
    
    Note: This event listener applies to ALL sync engines (including the one backing async).
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_sync_engine():
    """
    Create and configure a SYNC database engine for non-async operations.

    Used by:
    - Alembic migrations
    - Test scripts (populate_mock_data.py)
    - Check constraints script

    Returns:
        Engine: SQLAlchemy sync engine configured for SQLite
    """
    # Ensure database directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):  # relative path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    engine = create_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
        )
    return engine


def get_async_engine():
    """
    Create and configure the async database engine.

    Returns:
        AsyncEngine: SQLAlchemy async engine configured for SQLite with aiosqlite
    """
    # Ensure database directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):  # relative path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Convert sqlite:/// to sqlite+aiosqlite:/// for async
    async_db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    engine = create_async_engine(
        async_db_url,
        echo=False,
        # NullPool for SQLite - each connection is independent
        poolclass=NullPool,
        )
    return engine


# Create engine instances
sync_engine = get_sync_engine()  # For migrations, scripts
async_engine = get_async_engine()  # For FastAPI app


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session for dependency injection.

    Usage in FastAPI:
        @app.get("/")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            result = await session.exec(select(Model))
            ...

    Yields:
        AsyncSession: SQLModel async session
    """
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        yield session
