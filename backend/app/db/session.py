"""
Database session management.
Handles SQLite connection and session lifecycle with async support.
"""
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy import event, Engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings


# NOTE: settings is loaded lazily in get_sync_engine() and get_async_engine()
# to allow test setup to configure LIBREFOLIO_TEST_MODE before first use.
# Do NOT load settings at module level!


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


# ============================================================================
# ENGINE SINGLETON INSTANCES
# ============================================================================
# These are created ONCE at the first call, and reused throughout the app.
# The singleton pattern ensures a single connection pool per engine.

sync_engine: Engine | None = None  # For migrations, scripts populate, checks, populated in get_sync_engine()
async_engine: AsyncEngine | None = None  # For FastAPI app, populated in get_async_engine()


def get_sync_engine() -> Engine:
    """
    Create and configure a SYNC database engine for non-async operations.

    The singleton pattern is implemented and the generated engine is reused
    throughout the application.

    Used by:
    - Alembic migrations
    - Test scripts (populate_mock_data.py)
    - Check constraints script

    Returns:
        Engine: SQLAlchemy sync engine configured for SQLite
    """
    global sync_engine
    if sync_engine is not None:
        return sync_engine

    # Lazy load settings to allow test setup to configure environment first
    settings = get_settings()

    # Ensure database directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):  # relative path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    sync_engine = create_engine(
        db_url,
        echo=False,
        poolclass=NullPool,
        )
    return sync_engine


def get_async_engine() -> AsyncEngine:
    """
    Create and configure the async database engine.

    IMPORTANT: This function is called ONCE during module initialization
    to create the singleton async_engine instance. Do NOT call this function
    directly in application code - use the async_engine module variable instead.

    The singleton pattern is implemented and the generated engine is reused
    throughout the application.

    Returns:
        AsyncEngine: SQLAlchemy async engine configured for SQLite with aiosqlite
    """
    global async_engine
    if async_engine is not None:
        return async_engine

    # Lazy load settings to allow test setup to configure environment first
    settings = get_settings()

    # Ensure database directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):  # relative path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Convert sqlite:/// to sqlite+aiosqlite:/// for async
    async_db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

    async_engine = create_async_engine(
        async_db_url,
        echo=False,
        poolclass=NullPool,  # NullPool for SQLite - each connection is independent
        )
    return async_engine


# ============================================================================
# SESSION FACTORY
# ============================================================================

async def get_session_generator() -> AsyncGenerator[AsyncSession, None]:
    """
    Async session factory for FastAPI dependency injection.

    Creates a new session for each request from the singleton async_engine.
    The session is automatically closed after request completion.

    Architecture:
    - ONE async_engine instance (singleton, module-level)
    - MANY AsyncSession instances (one per request, short-lived)

    Usage in FastAPI:
        @app.get("/")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            result = await session.exec(select(Model))
            ...

    Yields:
        AsyncSession: SQLModel async session with expire_on_commit=False

    Note:
        expire_on_commit=False prevents lazy-loading errors when accessing
        committed objects outside the session context.
    """
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        yield session
