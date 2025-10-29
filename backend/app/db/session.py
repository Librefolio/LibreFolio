"""
Database session management.
Handles SQLite connection and session lifecycle.
"""
from typing import Generator
from pathlib import Path

from sqlalchemy import event, create_engine
from sqlalchemy.engine import Engine
from sqlmodel import Session

from backend.app.config import get_settings

settings = get_settings()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    Enable foreign key constraints for SQLite.
    This is required for proper referential integrity.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def get_engine():
    """
    Create and configure the database engine.

    Returns:
        Engine: SQLAlchemy engine configured for SQLite
    """
    # Ensure database directory exists
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if not db_path.startswith("/"):  # relative path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )
    return engine


# Create engine instance
engine = get_engine()


def get_session() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Use with FastAPI Depends() for automatic session management.

    Yields:
        Session: SQLModel session
    """
    with Session(engine) as session:
        yield session

