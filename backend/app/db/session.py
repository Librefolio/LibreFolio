"""
Database session management.
Handles SQLite connection and session lifecycle with async support.
"""

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import Engine, create_engine, event, false, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.config import get_settings

# NOTE: settings is loaded lazily in get_sync_engine() and get_async_engine()
# to allow test setup to configure LIBREFOLIO_TEST_MODE before first use.
# Do NOT load settings at module level!


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    """
    Enable essential SQLite PRAGMAs for proper operation.

    - trusted_schema=OFF, first (H-51): the SQL a database's schema keeps (a CHECK, a DEFAULT, a generated
      column, an index's expression) may call only the functions SQLite marks innocuous. SQLAlchemy's SQLite
      dialects register ``regexp`` and ``floor`` in Python on every connection; a restored archive's schema,
      which the restore check reads by kind only (B-28), could otherwise make every write call them with its own
      pattern. LibreFolio's own schema calls only the built-in ``lower()`` (``ux_users_email_lower``); top-level
      SQL is not restricted. ``writable_schema=RESET`` comes last, see below.
    - foreign_keys=ON: Required for referential integrity
    - journal_mode=WAL: Write-Ahead Logging — allows concurrent readers and
      one writer without blocking. Essential for the FX sync pipeline that
      reads route config in one session while writing rates in parallel sessions.
    - busy_timeout: WAL still admits **one writer at a time**, and SQLite's
      default on contention is to fail immediately rather than wait. Without
      this, a second writer arriving during another's transaction gets
      `database is locked` straight away — not after trying. That is reachable
      in production, not only under test: the scheduler refreshes prices in the
      background while the user saves a transaction, and uvicorn now runs with
      several workers.

      The value was 5000 on the assumption that no transaction here lasts that
      long. Measured, that was false: a full-history price sync committed 45k
      points in one transaction and held the write lock for 10.3s, so every
      concurrent writer failed. bulk_upsert_prices now commits in bounded
      slices (~1.2s each), but a slice's duration still scales with machine
      load and instrumentation — under coverage the same slices take four
      times longer. A timeout only decides how long a writer is willing to
      wait; waiting costs nothing when there is no contention, because the
      handler returns the moment the lock frees. Failing, by contrast, costs
      the user their write. 30s is chosen to absorb a queue of slices on a
      loaded machine rather than to match any single transaction.

    Note: This event listener applies to ALL sync engines (including the one backing async).
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA trusted_schema=OFF")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    # Last (H-51): journal_mode read the schema while regexp and floor did not exist yet — this listener runs before the
    # dialect registers them — so a CHECK or an index's expression calling them was read as an unknown function and never
    # marked as the schema's own. Reloaded at the next statement, with them registered, the schema is refused there.
    cursor.execute("PRAGMA writable_schema=RESET")
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


async def get_session_generator() -> AsyncGenerator[AsyncSession]:
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


async def begin_writes(session: AsyncSession, table: type) -> None:
    """Make SQLite open the transaction now, before the first SAVEPOINT of a write path (backlog W-B20).

    pysqlite defers ``BEGIN`` until the first write. A SAVEPOINT opened after only reads is then the outermost
    transaction, and its RELEASE commits: a later rollback can no longer undo it, and one failing step of a bulk
    operation cannot be rolled back on its own. An UPDATE of ``table`` that matches no row is a write to pysqlite, so it
    emits ``BEGIN``, and the savepoints opened after it nest inside one transaction. With a transaction already open it
    changes nothing. A global ``begin`` listener is not an option: a session that reads, sees another writer commit,
    then writes, would fail at once with ``SQLITE_BUSY_SNAPSHOT``.
    """
    key = next(iter(table.__table__.primary_key.columns))
    await session.execute(update(table).where(false()).values({key.name: key}).execution_options(synchronize_session=False))
